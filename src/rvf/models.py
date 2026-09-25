"""Forecasting models on one interface.

Every model is fitted inside a training window split into inner-train (first 80%) and
inner-validation (last 20%). Scalers are fitted on inner-train only. Log-space models map back
to variance levels with a SMEARING factor ``s = mean(exp(e))`` computed from inner-validation
log residuals (Duan 1983): ``exp(E[log RV | x])`` estimates the conditional *median* under a
symmetric log error, not the conditional mean, so a plain ``exp`` is biased low.
All level forecasts are floored at the minimum RV of the training window (a predeclared,
training-only floor; no forecast is repaired after its outcome is seen).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def smear_factor(resid: np.ndarray, q: float = 0.01) -> float:
    """Robust Duan smearing factor: mean(exp(e)) after winsorizing the log residuals at their
    own q / 1-q quantiles.

    Plain mean(exp(e)) is dominated by a single large positive residual: on PG an inner-train
    HAR-X fit extrapolated on a few inner-validation rows and the factor reached 3.6e8
    (development counterexample, protocol amendment rvf-1). Winsorizing uses only the
    validation residuals themselves, so it stays a training-only quantity."""
    e = np.asarray(resid, dtype=float)
    lo, hi = np.quantile(e, [q, 1 - q])
    return float(np.mean(np.exp(np.clip(e, lo, hi))))


@dataclass
class Scaler:
    mu: np.ndarray
    sd: np.ndarray

    @classmethod
    def fit(cls, X: np.ndarray) -> Scaler:
        sd = X.std(axis=0)
        return cls(X.mean(axis=0), np.where(sd > 0, sd, 1.0))

    def __call__(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mu) / self.sd


def ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.c_[np.ones(len(X)), X]
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return beta


@dataclass
class FitResult:
    predict_log: callable  # X -> log-variance forecast (None for level models)
    predict_level: callable  # X -> level forecast before smearing/floor (level models only)
    smear: float = 1.0
    info: dict = field(default_factory=dict)


class OLSLog:
    name = "ols_log"

    def fit(self, Xtr, ytr, Xva, yva, cfg, seed):
        beta = ols(np.r_[Xtr, Xva], np.r_[ytr, yva])
        beta_inner = ols(Xtr, ytr)
        res_va = yva - np.c_[np.ones(len(Xva)), Xva] @ beta_inner
        return FitResult(
            lambda X: np.c_[np.ones(len(X)), X] @ beta,
            None,
            smear_factor(res_va),
            {"beta": beta.tolist()},
        )


class OLSLevel:
    """Corsi (2009) HAR in levels: RV_{t+1} = b0 + bd RV_d + bw RV_w + bm RV_m (no transform)."""

    name = "ols_level"

    def fit(self, Xtr, ytr, Xva, yva, cfg, seed):
        beta = ols(np.r_[Xtr, Xva], np.r_[ytr, yva])
        return FitResult(
            None, lambda X: np.c_[np.ones(len(X)), X] @ beta, 1.0, {"beta": beta.tolist()}
        )


class RandomForest:
    name = "rf"

    def fit(self, Xtr, ytr, Xva, yva, cfg, seed):
        from sklearn.ensemble import RandomForestRegressor

        c = cfg["rf"]
        best = None
        for leaf in c["min_samples_leaf"]:
            for depth in c["max_depth"]:
                m = RandomForestRegressor(
                    n_estimators=c["n_estimators"],
                    max_features=c["max_features"],
                    min_samples_leaf=leaf,
                    max_depth=depth,
                    random_state=seed,
                    n_jobs=cfg.get("threads", 2),
                ).fit(Xtr, ytr)
                e = float(np.mean((yva - m.predict(Xva)) ** 2))
                if best is None or e < best[0]:
                    best = (e, leaf, depth, m)
        _, leaf, depth, m_inner = best
        smear = smear_factor(yva - m_inner.predict(Xva))
        final = RandomForestRegressor(
            n_estimators=c["n_estimators"],
            max_features=c["max_features"],
            min_samples_leaf=leaf,
            max_depth=depth,
            random_state=seed,
            n_jobs=cfg.get("threads", 2),
        ).fit(np.r_[Xtr, Xva], np.r_[ytr, yva])
        return FitResult(final.predict, None, smear, {"min_samples_leaf": leaf, "max_depth": depth})


def _torch_train(model, Xtr, ytr, Xva, yva, lr, batch, max_epochs, patience, l1, seed):
    import torch

    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    Xt, yt = torch.tensor(Xtr, dtype=torch.float32), torch.tensor(ytr, dtype=torch.float32)
    Xv, yv = torch.tensor(Xva, dtype=torch.float32), torch.tensor(yva, dtype=torch.float32)
    g = torch.Generator().manual_seed(seed)
    best, best_state, bad, epochs = np.inf, None, 0, 0
    for epoch in range(max_epochs):
        model.train()
        perm = torch.randperm(len(Xt), generator=g)
        for i in range(0, len(Xt), batch):
            idx = perm[i : i + batch]
            loss = torch.mean((model(Xt[idx]) - yt[idx]) ** 2)
            if l1:
                loss = loss + l1 * sum(
                    p.abs().sum() for n, p in model.named_parameters() if "weight" in n
                )
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            v = float(torch.mean((model(Xv) - yv) ** 2))
        epochs = epoch + 1
        if v < best - 1e-8:
            best, bad = v, 0
            best_state = {k: t.detach().clone() for k, t in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    return model, best, epochs


class FeedForward:
    """Feed-forward network NN3 of Christensen, Siggaard & Veliyev: three hidden layers of 16, 8
    and 4 neurons (sizes from the config) with leaky ReLU (slope 0.01), trained on standardized
    log RV with early stopping; ensemble mean over seeds."""

    name = "nn"

    def fit(self, Xtr, ytr, Xva, yva, cfg, seed):
        import torch
        from torch import nn

        c = cfg["nn"]
        sx = Scaler.fit(Xtr)
        ym, ys = float(ytr.mean()), float(ytr.std())
        nets, epochs = [], []
        for s in c["seeds"]:
            torch.manual_seed(seed * 100 + s)
            layers, prev = [], Xtr.shape[1]
            for h in c["layers"]:
                layers += [nn.Linear(prev, h), nn.LeakyReLU(0.01)]
                prev = h
            net = nn.Sequential(*layers, nn.Linear(prev, 1), nn.Flatten(0))
            net, _, ep = _torch_train(
                net,
                sx(Xtr),
                (ytr - ym) / ys,
                sx(Xva),
                (yva - ym) / ys,
                c["lr"],
                c["batch"],
                c["max_epochs"],
                c["patience"],
                c["l1"],
                seed * 100 + s,
            )
            nets.append(net)
            epochs.append(ep)

        def predict(X):
            with torch.no_grad():
                Xt = torch.tensor(sx(X), dtype=torch.float32)
                return np.mean([n(Xt).numpy() for n in nets], axis=0) * ys + ym

        smear = smear_factor(yva - predict(Xva))
        return FitResult(predict, None, smear, {"epochs": epochs})


class LSTMModel:
    """One-layer LSTM over the last ``lookback`` feature vectors (the original exercise's
    addition to the paper's comparison). Sequences are built from rows <= t only."""

    name = "lstm"

    def fit(self, Xtr_seq, ytr, Xva_seq, yva, cfg, seed):
        import torch
        from torch import nn

        c = cfg["lstm"]
        flat = Xtr_seq.reshape(-1, Xtr_seq.shape[-1])
        sx = Scaler.fit(flat)
        ym, ys = float(ytr.mean()), float(ytr.std())

        class Net(nn.Module):
            def __init__(self, k):
                super().__init__()
                self.lstm = nn.LSTM(k, c["hidden"], batch_first=True)
                self.drop = nn.Dropout(c["dropout"])
                self.out = nn.Linear(c["hidden"], 1)

            def forward(self, x):
                _, (h, _) = self.lstm(x)
                return self.out(self.drop(h[-1])).squeeze(-1)

        nets, epochs = [], []
        for s in c["seeds"]:
            torch.manual_seed(seed * 100 + s)
            net, _, ep = _torch_train(
                Net(Xtr_seq.shape[-1]),
                sx(Xtr_seq),
                (ytr - ym) / ys,
                sx(Xva_seq),
                (yva - ym) / ys,
                c["lr"],
                c["batch"],
                c["max_epochs"],
                c["patience"],
                0.0,
                seed * 100 + s,
            )
            nets.append(net)
            epochs.append(ep)

        def predict(Xseq):
            with torch.no_grad():
                Xt = torch.tensor(sx(Xseq), dtype=torch.float32)
                return np.mean([n(Xt).numpy() for n in nets], axis=0) * ys + ym

        smear = smear_factor(yva - predict(Xva_seq))
        return FitResult(predict, None, smear, {"epochs": epochs})


def sequences(X: np.ndarray, rows: np.ndarray, lookback: int) -> np.ndarray:
    """Stack X[t-lookback+1..t] for each t in ``rows`` (requires t >= lookback - 1)."""
    idx = rows[:, None] + np.arange(-lookback + 1, 1)[None, :]
    if idx.min() < 0:
        raise ValueError("sequence would reach before the first row")
    return X[idx]
