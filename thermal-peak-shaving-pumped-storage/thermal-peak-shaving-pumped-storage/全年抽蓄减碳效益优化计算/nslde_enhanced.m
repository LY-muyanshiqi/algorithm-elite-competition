function [chromosome, history] = nslde_enhanced(Nh, Nw, Np, L, Zpump, h, Cprice, options)
% nslde_enhanced - NSLDE :  + 
%
%  nslde.m:
%   1.  ( options.op_probs)
%   2.  (50HVIGD)
%   3.  ( options.init_method)
%   4. 
%
% :
%   options.init_method - 'logistic'|'tent'|'sobol'|'random' ('logistic')
%   options.op_probs    - 7 ()
%   options.pop         -  (100)
%   options.gen         -  (3000)
%   options.track_hv    - HV (true)
%   options.use_qlearning - Q-Learning (false)
%   options.track_strategy -  (false)
%
% :
%   chromosome - 
%   history    - 

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
initial_obj = chromosome(:, V+1:V+M);
initial_feasible = all(isfinite(initial_obj), 2);
if any(initial_feasible)
    hv_ref_point = max(initial_obj(initial_feasible, :), [], 1) * 1.2;
else
    hv_ref_point = [1e5, 1e10];
end

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
[history] = record_history(history, chromosome, M, V, entry_idx, hv_ref_point);
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
            state_features = extract_state_features(chromosome, M, V, i, gen, stagnation_counter, prev_hv, hv_ref_point);
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
        [history] = record_history(history, chromosome, M, V, entry_idx, hv_ref_point);
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

function [history] = record_history(history, chromosome, M, V, idx, hv_ref_point)
    N = size(chromosome, 1);

    f1 = chromosome(:, V+1);
    f2 = chromosome(:, V+2);
    % A failed objective may be NaN as well as +/-Inf.  Treat only finite
    % objective pairs as feasible so history statistics cannot be poisoned.
    feasible_mask = isfinite(f1) & isfinite(f2);

    history.gen(idx) = (idx - 1) * max(50, 1);
    history.n_feasible(idx) = sum(feasible_mask);
    if history.n_feasible(idx) > 0
        history.obj1_mean(idx) = mean(f1(feasible_mask));
        history.obj2_mean(idx) = mean(f2(feasible_mask));
    else
        % History is consumed by charts/RL state, so keep the empty-episode
        % summary finite.  The separate solution metrics retain Inf as the
        % infeasible sentinel.
        history.obj1_mean(idx) = 0;
        history.obj2_mean(idx) = 0;
    end
    if history.n_feasible(idx) > 1
        history.obj1_std(idx) = std(f1(feasible_mask));
        history.obj2_std(idx) = std(f2(feasible_mask));
    else
        history.obj1_std(idx) = 0;
        history.obj2_std(idx) = 0;
    end
    crowding_values = chromosome(feasible_mask, V+M+2);
    crowding_values = crowding_values(isfinite(crowding_values));
    if isempty(crowding_values)
        history.crowding_mean(idx) = 0;
        history.crowding_std(idx) = 0;
    else
        history.crowding_mean(idx) = mean(crowding_values);
        if numel(crowding_values) > 1
            history.crowding_std(idx) = std(crowding_values);
        else
            history.crowding_std(idx) = 0;
        end
    end

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

    history.hv(idx) = compute_hv_2d([f1(feasible_mask), f2(feasible_mask)], hv_ref_point);

    if history.n_feasible(idx) > 1
        f_all = [f1(feasible_mask), f2(feasible_mask)];
        ref_front = pareto_front(f_all);
        history.igd(idx) = compute_igd_2d(ref_front, f_all);
    else
        history.igd(idx) = 0;
    end
end

function ref = pareto_front(points)
    n = size(points, 1);
    is_front = true(n, 1);
    for i = 1:n
        for j = 1:n
            if i ~= j
                if (points(j,1) <= points(i,1) && points(j,2) <= points(i,2)) && ...
                   (points(j,1) < points(i,1) || points(j,2) < points(i,2))
                    is_front(i) = false;
                    break;
                end
            end
        end
    end
    ref = points(is_front, :);
end

function hv = compute_hv_2d(points, ref_point)
    if isempty(points), hv = 0; return; end
    points = double(points);
    ref_point = double(ref_point(:)');
    if size(points, 2) ~= 2 || numel(ref_point) ~= 2 || any(~isfinite(ref_point))
        error('points must be N-by-2 and ref_point must contain two finite values');
    end
    points = points(all(isfinite(points), 2), :);
    points = points(points(:, 1) < ref_point(1) & points(:, 2) < ref_point(2), :);
    if isempty(points), hv = 0; return; end
    points = sortrows(points, [1 2]);
    front = zeros(size(points));
    count = 0;
    best_y = inf;
    for i = 1:size(points, 1)
        if points(i, 2) < best_y
            count = count + 1;
            front(count, :) = points(i, :);
            best_y = points(i, 2);
        end
    end
    front = front(1:count, :);
    widths = diff([front(:, 1); ref_point(1)]);
    heights = ref_point(2) - front(:, 2);
    hv = sum(widths .* heights);
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

function features = extract_state_features(chromosome, M, V, gen, max_gen, stagnation, prev_hv, hv_ref_point)
    f1 = chromosome(:, V+1);
    f2 = chromosome(:, V+2);
    feasible = isfinite(f1) & isfinite(f2);
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
        hv_current = compute_hv_2d(f_all, hv_ref_point);
        hv_delta = (hv_current - prev_hv) / max(prev_hv, 1);
    end

    cv_rate = 1 - n_feasible / size(chromosome, 1);

    crowd_var = 0;
    if n_feasible > 2
        crowd_vals = chromosome(feasible, V+M+2);
        crowd_vals = crowd_vals(isfinite(crowd_vals));
        if numel(crowd_vals) > 1
            crowd_mean = mean(crowd_vals);
            crowd_var = min(max(std(crowd_vals) / max(abs(crowd_mean), 1e-10), 0), 1);
        end
    end

    features = [entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var];
end
