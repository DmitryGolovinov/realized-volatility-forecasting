# References

Checked against Crossref metadata on 2026-09-23.

| Source | Role | Used | Differs |
|---|---|---|---|
| Corsi (2009) | implemented benchmark | HAR in levels | |
| Christensen, Siggaard & Veliyev | partially replicated comparison | HAR, HAR-X, RF, feed-forward NN3 (16-8-4) horse race on realized variance | their sample is 29 DJIA stocks, 2001-01-29..2017-12-31 (4,235 days, working paper); here five supplied stocks without dates; log-RV training with smearing instead of level targets; smaller NN ensemble; LSTM added (by the original exercise); pooled comparison and forecast combination are new |
| Gu, Kelly & Xiu (2020) | context | geometric-pyramid architectures (their NN3 is 32-16-8) that inspired Christensen et al.'s smaller NN1-NN4 | we use Christensen et al.'s NN3 (16-8-4) |
| Hochreiter & Schmidhuber (1997) | method | LSTM | |
| Duan (1983) | method | smearing retransformation | winsorized residuals (amendment rvf-1) |
| Patton (2011) | loss | QLIKE as a robust loss for variance forecasts | |
| Corsi & Reno (2012) | feature definition (context) | negative-part daily/weekly/monthly returns as leverage terms in HAR models (the supplied `r_d`, `r_w`, `r_m`; the crypto panel's analogues) | no continuous-time link is used |
| Newey & West (1987); Diebold & Mariano (1995) | inference | HAC t-statistics of loss differences | |
| Barndorff-Nielsen & Shephard (2002) | feature definition | realized quarticity (M/3) sum r^4, the complete-grid scaling; the span-aware version for missing bars is derived in docs/methodology.md | |

Version note for Christensen, Siggaard & Veliyev: first published online 2022-06-30 in the
*Journal of Financial Econometrics*; issue 21(5), 1680-1727 (2023). A correction was published
online 2022-08-24 (issue 23(1), 2025), https://doi.org/10.1093/jjfinec/nbac032. An
institution-hosted working paper is https://pure.au.dk/ws/files/208284743/rp21_03.pdf. The journal
version's DOI is cited; no later re-upload is treated as the original.

- F. Corsi. A Simple Approximate Long-Memory Model of Realized Volatility. *Journal of Financial
  Econometrics* 7(2), 174-196, 2009 (online 2008-11-07). https://doi.org/10.1093/jjfinec/nbp001
- K. Christensen, M. Siggaard, B. Veliyev. A Machine Learning Approach to Volatility
  Forecasting. *Journal of Financial Econometrics* 21(5), 1680-1727, 2023.
  https://doi.org/10.1093/jjfinec/nbac020
- S. Gu, B. Kelly, D. Xiu. Empirical Asset Pricing via Machine Learning. *The Review of Financial
  Studies* 33(5), 2223-2273, 2020. https://doi.org/10.1093/rfs/hhaa009
- S. Hochreiter, J. Schmidhuber. Long Short-Term Memory. *Neural Computation* 9(8), 1735-1780,
  1997. https://doi.org/10.1162/neco.1997.9.8.1735
- N. Duan. Smearing Estimate: A Nonparametric Retransformation Method. *Journal of the American
  Statistical Association* 78(383), 605-610, 1983. https://doi.org/10.1080/01621459.1983.10478017
- A. J. Patton. Volatility forecast comparison using imperfect volatility proxies. *Journal of
  Econometrics* 160(1), 246-256, 2011. https://doi.org/10.1016/j.jeconom.2010.03.034
- F. Corsi, R. Reno. Discrete-Time Volatility Forecasting With Persistent Leverage Effect and the
  Link With Continuous-Time Volatility Modeling. *Journal of Business & Economic Statistics* 30(3),
  368-380, 2012. https://doi.org/10.1080/07350015.2012.663261
- W. K. Newey, K. D. West. *Econometrica* 55(3), 703-708, 1987. https://doi.org/10.2307/1913610
- F. X. Diebold, R. S. Mariano. *Journal of Business & Economic Statistics* 13(3), 253-263, 1995.
  https://doi.org/10.1080/07350015.1995.10524599
- O. E. Barndorff-Nielsen, N. Shephard. Econometric analysis of realized volatility and its use in
  estimating stochastic volatility models. *Journal of the Royal Statistical Society: Series B* 64(2),
  253-280, 2002. https://doi.org/10.1111/1467-9868.00336
