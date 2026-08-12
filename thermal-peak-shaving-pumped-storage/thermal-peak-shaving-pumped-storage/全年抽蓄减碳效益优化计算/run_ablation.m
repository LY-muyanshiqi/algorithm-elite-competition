function run_ablation(day_idx, province, n_runs, output_dir)
% run_ablation - NSLDE消融实验MATLAB入口
%
% 7组配置 × n_runs次重复, 验证每个模块的独立贡献
%
% 输入:
%   day_idx   - 数据中的日索引 (1-365)
%   province  - 省份名 ('shaanxi'|'gansu'|'qinghai'|'ningxia')
%   n_runs    - 每组配置的重复次数 (默认5)
%   output_dir - 输出目录 (默认'./experiment_results')
%
% 输出: {output_dir}/ablation_{province}_day{day_idx}.mat
%   包含结构体数组 results(7, n_runs), 每个元素含:
%     .config_name, .run_id, .chromosome, .metrics, .history

if nargin < 3, n_runs = 5; end
if nargin < 4, output_dir = './experiment_results'; end

if ~exist(output_dir, 'dir'), mkdir(output_dir); end

data = load_province_data(province);
if day_idx > size(data.NH, 1)
    error('day_idx %d exceeds data size %d', day_idx, size(data.NH, 1));
end

Nh = data.NH(day_idx, :);
Nw = data.NW(day_idx, :);
Np = data.NP(day_idx, :);
L = data.FH(day_idx, :);
Zpump = data.Zpump;
h = data.h;
Cprice = data.Cprice;

configs = ablation_configs();

fprintf('=== Ablation Study: %s day %d, %d runs ===\n', province, day_idx, n_runs);

for c = 1:length(configs)
    cfg = configs(c);
    fprintf('  [%d/%d] %s: %s\n', c, length(configs), cfg.name, cfg.desc);

    for r = 1:n_runs
        rng(c * 1000 + r);

        options = struct();
        options.pop = 100;
        options.gen = 2000;
        options.init_method = cfg.init;
        options.track_hv = true;

        if strcmp(cfg.op_mode, 'fixed')
            options.op_probs = cfg.op_probs;
        elseif strcmp(cfg.op_mode, 'uniform')
            options.op_probs = ones(1, 7) / 7;
        elseif strcmp(cfg.op_mode, 'learned')
            options.op_probs = ones(1, 7) / 7;
        end

        [chromosome, history] = nslde_enhanced(Nh, Nw, Np, L, Zpump, h, Cprice, options);

        result.config_name = cfg.name;
        result.run_id = r;
        result.chromosome = chromosome;
        result.history = history;
        result.metrics = compute_solution_metrics(chromosome);

        results(c, r) = result;

        fprintf('    run %d/%d: feasible=%d/%d, f1=%.1f, f2=%.1f, hv=%.1f\n', ...
            r, n_runs, result.metrics.n_feasible, options.pop, ...
            result.metrics.f1_mean, result.metrics.f2_mean, result.history.hv(end));
    end
end

save(fullfile(output_dir, sprintf('ablation_%s_day%d.mat', province, day_idx)), 'results', 'configs');
fprintf('Results saved to %s\n', fullfile(output_dir, sprintf('ablation_%s_day%d.mat', province, day_idx)));
end

function data = load_province_data(province)
    data.NH = load('hydro.txt');
    data.NW = load('wind.txt');
    data.NP = load('solar.txt');
    data.FH = load('FH.txt');

    switch lower(province)
        case 'shaanxi'
            data.Zpump = 1400;
        case 'gansu'
            data.Zpump = 1400;
        case 'qinghai'
            data.Zpump = 800;
        case 'ningxia'
            data.Zpump = 600;
        otherwise
            data.Zpump = 1400;
    end
    data.h = 4;
    data.Cprice = 0.05;
end

function configs = ablation_configs()
    configs = [
        struct('name', 'A0_NSGAII_baseline', 'desc', 'Standard NSGA-II', ...
               'init', 'random', 'op_mode', 'fixed', 'op_probs', [0,0,0,0.5,0.5,0,0]),
        struct('name', 'A1_chaos_only', 'desc', '+ Logistic chaos init', ...
               'init', 'logistic', 'op_mode', 'fixed', 'op_probs', [0,0,0,0.5,0.5,0,0]),
        struct('name', 'A2_de_only', 'desc', '+ DE/rand/1', ...
               'init', 'random', 'op_mode', 'fixed', 'op_probs', [0.5,0,0,0,0.5,0,0]),
        struct('name', 'A3_levy_only', 'desc', '+ Levy mutation', ...
               'init', 'random', 'op_mode', 'fixed', 'op_probs', [0,0,0,0.5,0,0.5,0]),
        struct('name', 'A4_NSLDE', 'desc', 'Chaos+DE+Levy (NSLDE)', ...
               'init', 'logistic', 'op_mode', 'fixed', 'op_probs', [0.4,0,0,0,0,0.3,0.3]),
        struct('name', 'A5_NSLDE_osn', 'desc', 'NSLDE + OSN adaptive', ...
               'init', 'logistic', 'op_mode', 'learned', 'op_probs', []),
        struct('name', 'A6_NSLDE_full', 'desc', 'Full model (all modules)', ...
               'init', 'logistic', 'op_mode', 'uniform', 'op_probs', []),
    ];
end

function metrics = compute_solution_metrics(chromosome)
    M = 2;
    V = 23;
    f1 = chromosome(:, V+1);
    f2 = chromosome(:, V+2);
    feasible = ~isinf(f1) & ~isinf(f2);
    n_feasible = sum(feasible);

    metrics.n_feasible = n_feasible;
    metrics.feasibility_rate = n_feasible / size(chromosome, 1);

    if n_feasible > 0
        metrics.f1_mean = mean(f1(feasible));
        metrics.f2_mean = mean(f2(feasible));
        metrics.f1_min = min(f1(feasible));
        metrics.f2_min = min(f2(feasible));
    else
        metrics.f1_mean = inf;
        metrics.f2_mean = inf;
        metrics.f1_min = inf;
        metrics.f2_min = inf;
    end

    if n_feasible > 1
        metrics.f1_std = std(f1(feasible));
        metrics.f2_std = std(f2(feasible));
        metrics.spread = std(f1(feasible)) + std(f2(feasible));

        f_all = [f1(feasible), f2(feasible)];
        [~, idx] = sort(f_all(:, 1));
        f_sorted = f_all(idx, :);
        sp = 0;
        for k = 1:size(f_sorted, 1) - 1
            sp = sp + norm(f_sorted(k+1, :) - f_sorted(k, :));
        end
        metrics.spacing = sp / (size(f_sorted, 1) - 1);
    else
        metrics.f1_std = 0;
        metrics.f2_std = 0;
        metrics.spread = 0;
        metrics.spacing = 0;
    end
end