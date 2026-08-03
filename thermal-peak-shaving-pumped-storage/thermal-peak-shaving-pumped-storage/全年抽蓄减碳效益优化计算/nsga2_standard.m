function chromosome = nsga2_standard(Nh, Nw, Np, L, Zpump, h, Cprice)
% NSGA-II 标准实现 — 用于对比实验
% nslde.m 的变体：移除 Levy 飞行扰动和 Logistic 混沌初始化
% 其余结构（锦标赛选择、非支配排序、替换策略）与 nslde.m 完全一致

pop = round(100);
gen = round(3000);
[M, V, min_range, max_range] = objective_description_function();

% === 关键差异1: 随机初始化（无混沌映射） ===
chromosome = initialize_variables_rand(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
chromosome = non_domination_sort_mod(chromosome, M, V);

for i = 1:gen
    pool = round(pop/2);
    tour = 2;
    parent_chromosome = tournament_selection(chromosome, pool, tour);

    % === 关键差异2: 标准遗传算子（无 Levy 飞行） ===
    offspring_chromosome = genetic_operator_normal(parent_chromosome, chromosome, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);

    [main_pop, ~] = size(chromosome);
    [offspring_pop, ~] = size(offspring_chromosome);
    intermediate_chromosome(1:main_pop, :) = chromosome;
    intermediate_chromosome(main_pop+1:main_pop+offspring_pop, 1:M+V) = offspring_chromosome;
    intermediate_chromosome = non_domination_sort_mod(intermediate_chromosome, M, V);
    chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);

    if ~mod(i, 100)
        clc
        fprintf('%d generations completed (NSGA-II)\n', i);
    end
end
end

% === 随机初始化（替代 Logistic 混沌映射） ===
function f = initialize_variables_rand(N, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice)
    K = M + V;
    for i = 1:N
        for j = 1:V
            f(i, j) = min_range(j) + (max_range(j) - min_range(j)) * rand(1);
        end
        f(i, V+1:K) = evaluate_objective(f(i,:), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    end
end

% === 标准遗传算子（DE/rand/1 + 多项式变异，无 Levy 飞行） ===
function f = genetic_operator_normal(parent_chromosome, chromosome, M, V, l_limit, u_limit, Nh, Nw, Np, L, Zpump, h, Cprice)
    [N, ~] = size(parent_chromosome);
    p = 1;
    child = [];
    for i = 1:N
        parent_1 = round(N * rand(1));
        if parent_1 < 1, parent_1 = 1; end
        parent_2 = round(N * rand(1));
        if parent_2 < 1, parent_2 = 1; end
        while isequal(parent_chromosome(parent_1, :), parent_chromosome(parent_2, :))
            parent_2 = round(N * rand(1));
            if parent_2 < 1, parent_2 = 1; end
        end
        p1 = parent_chromosome(parent_1, :);
        p2 = parent_chromosome(parent_2, :);
        for j = 1:V
            % DE/rand/1 差分变异 (F=0.65)
            if rand(1) < 0.7
                child_1(j) = parent_chromosome(i, j) + 0.65 * (p1(j) - p2(j));
            else
                child_1(j) = parent_chromosome(i, j);
            end
            % 多项式变异 (pm=1/V, mum=20)
            r = rand(1);
            if r < 1/V
                if r < 0.5
                    delta = (2*r)^(1/21) - 1;
                else
                    delta = 1 - (2*(1-r))^(1/21);
                end
                child_1(j) = child_1(j) + delta * (u_limit(j) - l_limit(j));
            end
            if child_1(j) > u_limit(j), child_1(j) = u_limit(j); end
            if child_1(j) < l_limit(j), child_1(j) = l_limit(j); end
        end
        child_1(:, V+1:M+V) = evaluate_objective(child_1, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
        child(p, :) = child_1;
        p = p + 1;
    end
    f = child;
end
