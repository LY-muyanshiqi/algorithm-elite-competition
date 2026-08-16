% ablation_mechanism.m - 框架内三机制消融
% 在单算子框架(nslde_enhanced)内，逐项加机制，看低代数下可行解收敛速度
clear;

Nh = load('ningxia_hydro.txt'); Nw = load('ningxia_wind.txt');
Np = load('ningxia_solar.txt'); L = load('ningxia_fh.txt');
Zpump = 600;

day = 1;  % 宁夏最难天之一
pop_size = 50;
n_gen = 100;  % 低代数，暴露收敛速度差异
n_runs = 15;

% 消融配置
configs = {
    'E0_no_mech',       'random',   [0,0,0,0.5,0.5,0,0];
    'E1_chaos',         'logistic', [0,0,0,0.5,0.5,0,0];
    'E2_chaos_DE',      'logistic', [0.5,0,0,0,0.5,0,0];
    'E2b_chaos_levy',   'logistic', [0,0,0,0.5,0,0.5,0];
    'E3_full_NSLDE',    'logistic', [0.4,0,0,0,0,0.3,0.3];
};

fprintf('=== 三机制框架内消融 (宁夏 day %d, gen=%d, %d次) ===\n', day, n_gen, n_runs);

results = struct();
for c = 1:size(configs, 1)
    cname = configs{c,1};
    init = configs{c,2};
    op_probs = configs{c,3};

    n_feas_all = zeros(n_runs, 1);
    f1_mins = zeros(n_runs, 1);
    for r = 1:n_runs
        rng(c*10000 + r);
        options = struct('pop', pop_size, 'gen', n_gen, 'init_method', init, 'track_hv', false, 'op_probs', op_probs);
        [chromosome, ~] = nslde_enhanced(Nh(day,:), Nw(day,:), Np(day,:), L(day,:), Zpump, 4, 0.05, options);
        f1 = chromosome(:, 24); f2 = chromosome(:, 25);
        fea = ~isinf(f1) & ~isinf(f2);
        n_feas_all(r) = sum(fea);
        if any(fea), f1_mins(r) = min(f1(fea)); else, f1_mins(r) = nan; end
    end
    results.(cname).n_feas = n_feas_all;
    results.(cname).f1_min = f1_mins;
    fprintf('  %-18s: 可行解 mean=%.1f/%.0f  f1_min mean=%.0f\n', ...
        cname, mean(n_feas_all), pop_size, nanmean(f1_mins));
end

save('ablation_mechanism.mat', 'results', 'configs', 'day', 'pop_size', 'n_gen', 'n_runs');
fprintf('\n结果已存 ablation_mechanism.mat\n');
