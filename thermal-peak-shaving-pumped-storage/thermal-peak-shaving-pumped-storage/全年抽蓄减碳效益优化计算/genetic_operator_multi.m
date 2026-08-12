function f = genetic_operator_multi(parent_chromosome, chromosome, M, V, l_limit, u_limit, Nh, Nw, Np, L, Zpump, h, Cprice, op_probs)
% genetic_operator_multi - 
%
%  genetic_operator.m :
%   1. 7 op_probs 
%   2. 
%   3.  op_probs 
%
% :
%   op_probs - 7
%              [DE_rand_1, DE_rand_2, DE_current_to_best, PM, SBX, Levy, Cauchy]
%
% :
%   1: DE/rand/1      - 
%   2: DE/rand/2      - 
%   3: DE/current-to-best/1 - 
%   4: PM () - 
%   5: SBX () - 
%   6: Levy        - 
%   7: Cauchy      - 

if nargin < 16
    op_probs = ones(1,7) / 7;
end

op_probs = op_probs / sum(op_probs);
op_cumsum = cumsum(op_probs);

[N, ~] = size(parent_chromosome);
p = 1;
child = [];

for i = 1:N
    child_1 = [];
    child_2 = [];

    parent_1_idx = randi(N);
    parent_2_idx = randi(N);
    while parent_2_idx == parent_1_idx
        parent_2_idx = randi(N);
    end
    parent_1 = parent_chromosome(parent_1_idx, :);
    parent_2 = parent_chromosome(parent_2_idx, :);

    r = rand();
    op_id = find(op_cumsum >= r, 1, 'first');

    switch op_id
        case 1
            [child_1, child_2] = op_de_rand_1(parent_chromosome(i,:), parent_1, parent_2, V, l_limit, u_limit);
        case 2
            [child_1, child_2] = op_de_rand_2(parent_chromosome(i,:), parent_1, parent_2, parent_chromosome, V, l_limit, u_limit);
        case 3
            [child_1, child_2] = op_de_current_to_best(parent_chromosome(i,:), parent_1, parent_2, chromosome, V, l_limit, u_limit);
        case 4
            [child_1, child_2] = op_pm(parent_chromosome(i,:), V, l_limit, u_limit);
        case 5
            [child_1, child_2] = op_sbx(parent_chromosome(i,:), parent_1, parent_2, V, l_limit, u_limit);
        case 6
            [child_1, child_2] = op_levy(parent_chromosome(i,:), V, l_limit, u_limit);
        case 7
            [child_1, child_2] = op_cauchy(parent_chromosome(i,:), V, l_limit, u_limit);
    end

    child_1(:, V+1:M+V) = evaluate_objective(child_1, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    child_2(:, V+1:M+V) = evaluate_objective(child_2, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);

    child(p, :) = child_1;
    child(p+1, :) = child_2;
    p = p + 2;
end

f = child;
end

%% ====== 1: DE/rand/1 ======
function [c1, c2] = op_de_rand_1(target, p1, p2, V, l_limit, u_limit)
    F = 0.5;
    CR = 0.9;
    for j = 1:V
        if rand() < CR
            c1(j) = p1(j) + F * (p2(j) - target(1,j));
        else
            c1(j) = target(j);
        end
    end
    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = target(1:V);
end

%% ====== 2: DE/rand/2 ======
function [c1, c2] = op_de_rand_2(target, p1, p2, pop, V, l_limit, u_limit)
    N = size(pop, 1);
    idx3 = randi(N);
    idx4 = randi(N);
    while idx4 == idx3, idx4 = randi(N); end
    p3 = pop(idx3, 1:V);
    p4 = pop(idx4, 1:V);

    F = 0.5;
    CR = 0.9;
    for j = 1:V
        if rand() < CR
            c1(j) = p1(j) + F * (p2(j) - p3(j)) + F * (p4(j) - target(1,j));
        else
            c1(j) = target(j);
        end
    end
    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = target(1:V);
end

%% ====== 3: DE/current-to-best/1 ======
function [c1, c2] = op_de_current_to_best(target, p1, p2, pop, V, l_limit, u_limit)
    [~, best_idx] = sort(pop(:, V+1));
    best = pop(best_idx(1), 1:V);

    F1 = 0.8;
    F2 = 0.5;
    CR = 0.9;
    for j = 1:V
        if rand() < CR
            c1(j) = target(j) + F1 * (best(j) - target(j)) + F2 * (p1(j) - p2(j));
        else
            c1(j) = target(j);
        end
    end
    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = target(1:V);
end

%% ====== 4:  PM ======
function [c1, c2] = op_pm(parent, V, l_limit, u_limit)
    eta_m = 20;
    pm = 1/V;

    c1 = parent(1:V);
    c2 = parent(1:V);

    for j = 1:V
        if rand() < pm
            y = parent(j);
            delta1 = (y - l_limit(j)) / (u_limit(j) - l_limit(j));
            delta2 = (u_limit(j) - y) / (u_limit(j) - l_limit(j));

            r = rand();
            if r <= 0.5
                delta_q = (2*r)^(1/(eta_m+1)) - 1;
                c1(j) = y + delta_q * (u_limit(j) - l_limit(j));
            else
                delta_q = 1 - (2*(1-r))^(1/(eta_m+1));
                c1(j) = y + delta_q * (u_limit(j) - l_limit(j));
            end

            r2 = rand();
            if r2 <= 0.5
                delta_q2 = (2*r2)^(1/(eta_m+1)) - 1;
                c2(j) = y + delta_q2 * (u_limit(j) - l_limit(j));
            else
                delta_q2 = 1 - (2*(1-r2))^(1/(eta_m+1));
                c2(j) = y + delta_q2 * (u_limit(j) - l_limit(j));
            end
        end
    end
    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = clip_bounds(c2, l_limit, u_limit);
end

%% ====== 5: SBX  ======
function [c1, c2] = op_sbx(p1, p2_parent, p3, V, l_limit, u_limit)
    eta_c = 20;
    pc = 0.9;

    c1 = p1(1:V);
    c2 = p1(1:V);

    if rand() < pc
        for j = 1:V
            if rand() < 0.5
                if abs(p2_parent(j) - p3(j)) > 1e-14
                    y1 = min(p2_parent(j), p3(j));
                    y2 = max(p2_parent(j), p3(j));

                    beta = 1 + 2*(y1 - l_limit(j)) / max(y2 - y1, 1e-14);
                    alpha = 2 - beta^(-(eta_c+1));

                    r = rand();
                    if r <= 1/alpha
                        beta_q = (r * alpha)^(1/(eta_c+1));
                    else
                        beta_q = (1/(2 - r*alpha))^(1/(eta_c+1));
                    end

                    c1(j) = 0.5 * ((y1 + y2) - beta_q * (y2 - y1));

                    beta2 = 1 + 2*(u_limit(j) - y2) / max(y2 - y1, 1e-14);
                    alpha2 = 2 - beta2^(-(eta_c+1));

                    r2 = rand();
                    if r2 <= 1/alpha2
                        beta_q2 = (r2 * alpha2)^(1/(eta_c+1));
                    else
                        beta_q2 = (1/(2 - r2*alpha2))^(1/(eta_c+1));
                    end

                    c2(j) = 0.5 * ((y1 + y2) + beta_q2 * (y2 - y1));
                end
            end
        end
    end
    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = clip_bounds(c2, l_limit, u_limit);
end

%% ====== 6: Levy  ======
function [c1, c2] = op_levy(target, V, l_limit, u_limit)
    beta = 1.5;
    sigma_u = (gamma(1+beta)*sin(pi*beta/2) / (gamma((1+beta)/2)*beta*2^((beta-1)/2)))^(1/beta);

    u = normrnd(0, sigma_u, 1, V);
    v = normrnd(0, 1, 1, V);
    step = u ./ (abs(v).^(1/beta));

    alpha = 0.01;
    c1 = target(1:V) + alpha * step .* (u_limit - l_limit);

    r = -1 + 2*rand(1, V);
    c2 = target(1:V) + alpha * r .* (u_limit - l_limit);

    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = clip_bounds(c2, l_limit, u_limit);
end

%% ====== 7: Cauchy  ======
function [c1, c2] = op_cauchy(target, V, l_limit, u_limit)
    alpha = 0.01;
    cauchy_noise1 = tan(pi*(rand(1,V) - 0.5));
    c1 = target(1:V) + alpha * cauchy_noise1 .* (u_limit - l_limit);

    cauchy_noise2 = tan(pi*(rand(1,V) - 0.5));
    c2 = target(1:V) + alpha * cauchy_noise2 .* (u_limit - l_limit);

    c1 = clip_bounds(c1, l_limit, u_limit);
    c2 = clip_bounds(c2, l_limit, u_limit);
end

%% ====== Boundary handling ======
function x = clip_bounds(x, l_limit, u_limit)
    for j = 1:length(x)
        if x(j) > u_limit(j)
            x(j) = u_limit(j);
        elseif x(j) < l_limit(j)
            x(j) = l_limit(j);
        end
    end
end
