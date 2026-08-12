function p = params()
p = struct();

p.POP = 100;
p.GEN = 3000;
p.pool = 50;
p.tour = 2;

p.V = 23;
p.M = 2;

p.F = 0.3;
p.pc = 0.7;
p.pm = 0.5;

p.alpha_levy = 0.5;
p.beta_levy = 1.5;
p.sigma_u = 0.6966;

p.eta_m = 20;
p.eta_c = 20;

p.F1 = 0.8;
p.F2 = 0.5;
p.CR = 0.9;

p.carbon_price = 100;

p.n_operators = 7;

p.init_method = 'logistic';

p.track_interval = 50;
p.track_hv = true;
end