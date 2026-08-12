function [chromosome, history] = nslde_enhanced(Nh, Nw, Np, L, Zpump, h, Cprice, options)
% nslde_enhanced - NSLDE 增强版: 多算子自适应 + 迭代历史记录
%
% 相较于原 nslde.m:
%   1. 支持多算子自适应选择 (通过 options.op_probs)
%   2. 记录完整进化轨迹 (每50代的HV、IGD、种群熵等)
%   3. 支持多种初始化策略 (通过 options.init_method)
%   4. 可配置种群大小和代数
%
% 输入:
%   options.init_method - 'logistic'|'tent'|'sobol'|'random' (默认'logistic')
%   options.op_probs    - 7维算子概率向量 (默认均匀)
%   options.pop         - 种群大小 (默认100)
%   options.gen         - 进化代数 (默认3000)
%   options.track_hv    - 是否追踪HV (默认true)
%   options.use_qlearning - 是否使用Q-Learning自适应 (默认false)
%   options.track_strategy - 是否追踪策略使用 (默认false)
%
% 输出:
%   chromosome - 最终种群
%   history    - 进化历史结构体

if nargin < 8
    options = struct();
end

if ~isfield(options, 'pop'), options.pop = 100; end
if ~isfield(options, 'gen'), options.gen = 3000; end
if ~isfield(options, 'init_method'), options.init_method = 'logistic'; end
if ~isfield(options, 'track_hv'), options.track_hv = false; end
if ~isfield(options, 'use_qlearning'), options.use_qlearning = false; end
if ~isfield(options, 'track_strategy'), options.track_strategy = false; end

pop = options.pop;
gen = options.gen;
init_method = options.init_method;

[M, V, min_range, max_range] = objective_description_function();

%% Initialize population with selected strategy
chromosome = initialize_variables_multi(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice, init_method);
chromosome = non_domination_sort_mod(chromosome, M, V);

%% Initialize history tracking
track_interval = 50;
n_entries = floor(gen / track_interval) + 1;
history = struct();
history.gen = zeros(n_entries, 1);
history.hv = zeros(n_entries, 1);
history.entropy = zeros(n_entries, 1);
history.n_feasible = zeros(n_entries, 1);
history.igd = zeros(n_entries, 1);
history.crowding_mean = zeros(n_entries, 1);
history.crowding_std = zeros(n_entries, 1);
history.obj1_mean = zeros(n_entries, 1);
history.obj2_mean = zeros(n_entries, 1);
history.obj1_std = zeros(n_entries, 1);
history.obj2_std = zeros(n_entries, 1);

entry_idx = 1;
[history] = record_history(history, chromosome, M, V, entry_idx);
entry_idx = entry_idx + 1;

q_table = [];
epsilon = 0.3;
prev_hv = 0;
stagnation_counter = 0;
strategy_use_count = zeros(1, 7);
strategy_success_count = zeros(1, 7);
strategy_history = zeros(n_entries, 7);

%% Evolution loop
for i = 1:gen
    pool = round(pop / 2);
    tour = 2;

    parent_chromosome = tournament_selection(chromosome, pool, tour);

    if options.use_qlearning
        if mod(i, track_interval) == 0 || i == 1
            state_features = extract_state_features(chromosome, M, V, i, gen, stagnation_counter, prev_hv);
            if i == 1
                [op_probs_current, q_table, epsilon] = q_learning_selector(state_features, [], 0.3, 0, 0, i, gen);
            else
                hv_current = history.hv(entry_idx - 1);
                reward = (hv_current - prev_hv) / max(abs(hv_current), 1);
                if reward <= 0
                    stagnation_counter = stagnation_counter + 1;
                else
                    stagnation_counter = 0;
                end
                [op_probs_current, q_table, epsilon] = q_learning_selector(state_features, q_table, epsilon, last_action, reward, i, gen);
                prev_hv = hv_current;
            end
            [~, last_action] = max(op_probs_current);
        end
    elseif isfield(options, 'op_probs')
        op_probs_current = options.op_probs;
    else
        op_probs_current = ones(1, 7) / 7;
    end

    offspring_chromosome = genetic_operator_multi(parent_chromosome, chromosome, M, V, ...
        min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice, op_probs_current);

    if options.track_strategy
        [~, dominant_op] = max(op_probs_current);
        strategy_use_count(dominant_op) = strategy_use_count(dominant_op) + 1;
    end

    [main_pop, ~] = size(chromosome);
    [offspring_pop, ~] = size(offspring_chromosome);

    intermediate_chromosome(1:main_pop, :) = chromosome;
    intermediate_chromosome(main_pop+1:main_pop+offspring_pop, 1:M+V) = offspring_chromosome;

    intermediate_chromosome = non_domination_sort_mod(intermediate_chromosome, M, V);
    chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);

    if mod(i, track_interval) == 0
        [history] = record_history(history, chromosome, M, V, entry_idx);
        if options.track_strategy
            strategy_history(entry_idx, :) = strategy_use_count / max(sum(strategy_use_count), 1);
        end
        entry_idx = entry_idx + 1;
        if ~mod(i, 500)
            clc
            fprintf('%d/%d generations completed\n', i, gen);
        end
    end
end

history.gen = history.gen(1:entry_idx-1);
history.hv = history.hv(1:entry_idx-1);
history.entropy = history.entropy(1:entry_idx-1);
history.n_feasible = history.n_feasible(1:entry_idx-1);
history.igd = history.igd(1:entry_idx-1);
history.crowding_mean = history.crowding_mean(1:entry_idx-1);
history.crowding_std = history.crowding_std(1:entry_idx-1);
history.obj1_mean = history.obj1_mean(1:entry_idx-1);
history.obj2_mean = history.obj2_mean(1:entry_idx-1);
history.obj1_std = history.obj1_std(1:entry_idx-1);
history.obj2_std = history.obj2_std(1:entry_idx-1);
if options.track_strategy
    history.strategy_history = strategy_history(1:entry_idx-1, :);
    history.strategy_use_count = strategy_use_count;
end

end

function [history] = record_history(history, chromosome, M, V, idx)
    N = size(chromosome, 1);

    f1 = chromosome(:, V+1);
    f2 = chromosome(:, V+2);
    feasible_mask = ~isinf(f1) & ~isinf(f2);

    history.gen(idx) = (idx - 1) * max(50, 1);
    history.n_feasible(idx) = sum(feasible_mask);
    history.obj1_mean(idx) = mean(f1(feasible_mask));
    history.obj2_mean(idx) = mean(f2(feasible_mask));
    history.obj1_std(idx) = std(f1(feasible_mask));
    history.obj2_std(idx) = std(f2(feasible_mask));
    history.crowding_mean(idx) = mean(chromosome(feasible_mask, V+M+2));
    history.crowding_std(idx) = std(chromosome(feasible_mask, V+M+2));

    if sum(feasible_mask) > 2
        f_all = [f1(feasible_mask), f2(feasible_mask)];
        f_all_norm = (f_all - min(f_all)) ./ (max(f_all) - min(f_all) + 1e-10);
        dist_matrix = pdist2(f_all_norm, f_all_norm);
        alpha = 0.1;
        S = exp(-dist_matrix.^2 / (2 * alpha^2));
        history.entropy(idx) = -mean(log(mean(S, 2) + 1e-10));
    else
        history.entropy(idx) = 0;
    end

    ref_point = [max(f1(feasible_mask)) * 1.2, max(f2(feasible_mask)) * 1.2];
    history.hv(idx) = compute_hv_2d([f1(feasible_mask), f2(feasible_mask)], ref_point);

    if history.n_feasible(idx) > 1 && exist('ref_pareto', 'var')
        history.igd(idx) = compute_igd_2d(ref_pareto, [f1(feasible_mask), f2(feasible_mask)]);
    else
        history.igd(idx) = 0;
    end
end

function hv = compute_hv_2d(points, ref_point)
    if isempty(points), hv = 0; return; end
    points = sortrows(points, 1);
    hv = 0;
    prev_x = ref_point(1);
    for i = 1:size(points, 1)
        if points(i, 2) < ref_point(2)
            hv = hv + (prev_x - points(i, 1)) * (ref_point(2) - points(i, 2));
            prev_x = points(i, 1);
        end
    end
    hv = abs(hv);
end

function igd = compute_igd_2d(ref, points)
    total = 0;
    for i = 1:size(ref, 1)
        min_d = inf;
        for j = 1:size(points, 1)
            d = norm(ref(i, :) - points(j, :));
            if d < min_d, min_d = d; end
        end
        total = total + min_d;
    end
    igd = total / size(ref, 1);
end

function features = extract_state_features(chromosome, M, V, gen, max_gen, stagnation, prev_hv)
    f1 = chromosome(:, V+1);
    f2 = chromosome(:, V+2);
    feasible = ~isinf(f1) & ~isinf(f2);
    n_feasible = sum(feasible);

    if n_feasible > 2
        f_all = [f1(feasible), f2(feasible)];
        f_all_norm = (f_all - min(f_all)) ./ (max(f_all) - min(f_all) + 1e-10);
        dist_matrix = pdist2(f_all_norm, f_all_norm);
        alpha = 0.1;
        S = exp(-dist_matrix.^2 / (2 * alpha^2));
        entropy = -mean(log(mean(S, 2) + 1e-10));
    else
        entropy = 0;
    end

    entropy_norm = min(max(entropy / 5, 0), 1);

    gen_ratio = gen / max_gen;

    stag_norm = min(stagnation / 10, 3);

    hv_delta = 0;
    if prev_hv > 0 && n_feasible > 0
        f_all = [f1(feasible), f2(feasible)];
        ref_point = [max(f1(feasible)) * 1.2, max(f2(feasible)) * 1.2];
        hv_current = compute_hv_2d(f_all, ref_point);
        hv_delta = (hv_current - prev_hv) / max(prev_hv, 1);
    end

    cv_rate = 1 - n_feasible / size(chromosome, 1);

    crowd_var = 0;
    if n_feasible > 2
        crowd_vals = chromosome(feasible, V+M+2);
        crowd_var = min(max(std(crowd_vals) / max(mean(crowd_vals), 1e-10), 0), 1);
    end

    features = [entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var];
end
