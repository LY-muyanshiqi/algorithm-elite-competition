function chromosome = nsga2_standard_sbx(Nh, Nw, Np, L, Zpump, h, Cprice, pop, gen)
% nsga2_standard_sbx - 真·标准 NSGA-II（SBX + 多项式变异 + 随机初始化）
%
% 作为三机制消融实验的干净基线。区别现有 nsga2_standard.m：
%   现有版误用了 DE/rand/1 交叉(伪NSGA-II)，本版用真正的 SBX 交叉
%   + 多项式变异，符合 Deb(2002) 原始定义。

if nargin < 8, pop = 100; end
if nargin < 9, gen = 3000; end

[M, V, min_range, max_range] = objective_description_function();

% 随机初始化
chromosome = initialize_variables_rand(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
chromosome = non_domination_sort_mod(chromosome, M, V);

for i = 1:gen
    pool = round(pop/2);
    tour = 2;
    parent_chromosome = tournament_selection(chromosome, pool, tour);
    offspring_chromosome = genetic_operator_sbx(parent_chromosome, chromosome, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);

    [main_pop, ~] = size(chromosome);
    [offspring_pop, ~] = size(offspring_chromosome);
    intermediate_chromosome(1:main_pop, :) = chromosome;
    intermediate_chromosome(main_pop+1:main_pop+offspring_pop, 1:M+V) = offspring_chromosome;
    intermediate_chromosome = non_domination_sort_mod(intermediate_chromosome, M, V);
    chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);
end
end

% 随机初始化
function f = initialize_variables_rand(N, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice)
    f = [];
    for i = 1:N
        for j = 1:V
            f(i, j) = min_range(j) + (max_range(j) - min_range(j)) * rand(1);
        end
        f(i, V+1:M+V) = evaluate_objective(f(i,:), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    end
end

% SBX 交叉 + 多项式变异（Deb 2002 标准）
function f = genetic_operator_sbx(parent_chromosome, chromosome, M, V, l_limit, u_limit, Nh, Nw, Np, L, Zpump, h, Cprice)
    [N, ~] = size(parent_chromosome);
    eta_c = 20;   % SBX 分布指数
    eta_m = 20;   % 多项式变异分布指数
    pc = 0.9;     % 交叉概率
    pm = 1/V;     % 变异概率

    p = 1;
    child = [];
    for i = 1:2:N
        % 选两个父代
        par1_idx = randi(N);
        par2_idx = randi(N);
        while par2_idx == par1_idx, par2_idx = randi(N); end
        parent1 = parent_chromosome(par1_idx, 1:V);
        parent2 = parent_chromosome(par2_idx, 1:V);

        child1 = parent1;
        child2 = parent2;

        % SBX 交叉
        if rand(1) < pc
            for j = 1:V
                if rand(1) < 0.5 && abs(parent1(j) - parent2(j)) > 1e-14
                    y1 = min(parent1(j), parent2(j));
                    y2 = max(parent1(j), parent2(j));
                    if (y2 - y1) < 1e-14, continue; end

                    beta = 1 + 2*(y1 - l_limit(j))/(y2 - y1);
                    alpha = 2 - beta^(-(eta_c+1));
                    u = rand(1);
                    if u <= 1/alpha
                        betaq = (u*alpha)^(1/(eta_c+1));
                    else
                        betaq = (1/(2-u*alpha))^(1/(eta_c+1));
                    end
                    child1(j) = 0.5*((y1+y2) - betaq*(y2-y1));

                    beta2 = 1 + 2*(u_limit(j) - y2)/(y2 - y1);
                    alpha2 = 2 - beta2^(-(eta_c+1));
                    u2 = rand(1);
                    if u2 <= 1/alpha2
                        betaq2 = (u2*alpha2)^(1/(eta_c+1));
                    else
                        betaq2 = (1/(2-u2*alpha2))^(1/(eta_c+1));
                    end
                    child2(j) = 0.5*((y1+y2) + betaq2*(y2-y1));
                end
            end
        end

        % 多项式变异
        for j = 1:V
            if rand(1) < pm
                u = rand(1);
                if u <= 0.5
                    delta = (2*u)^(1/(eta_m+1)) - 1;
                else
                    delta = 1 - (2*(1-u))^(1/(eta_m+1));
                end
                child1(j) = child1(j) + delta*(u_limit(j)-l_limit(j));
            end
            if rand(1) < pm
                u = rand(1);
                if u <= 0.5
                    delta = (2*u)^(1/(eta_m+1)) - 1;
                else
                    delta = 1 - (2*(1-u))^(1/(eta_m+1));
                end
                child2(j) = child2(j) + delta*(u_limit(j)-l_limit(j));
            end
        end

        % 边界裁剪
        for j = 1:V
            child1(j) = min(max(child1(j), l_limit(j)), u_limit(j));
            child2(j) = min(max(child2(j), l_limit(j)), u_limit(j));
        end

        child1(V+1:M+V) = evaluate_objective(child1, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
        child(p, :) = child1;
        p = p + 1;
        if i+1 <= N
            child2(V+1:M+V) = evaluate_objective(child2, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
            child(p, :) = child2;
            p = p + 1;
        end
    end
    f = child;
end
