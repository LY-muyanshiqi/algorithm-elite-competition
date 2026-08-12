function chromosome = moead_de(Nh, Nw, Np, L, Zpump, h, Cprice, pop, gen)
% moead_de - MOEA/D with DE operator (MOEA/D-DE)
%
% 标准 MOEA/D 框架 + DE/rand/1 交叉替代 SBX

if nargin < 8, pop = 100; end
if nargin < 9, gen = 200; end

[M, V, min_range, max_range] = objective_description_function();

T = min(20, pop - 1);
lambda = generate_weight_vectors(pop, M);

z_star = inf(1, M);

pop_chrom = initialize_variables(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);

for i = 1:pop
    for j = 1:M
        if pop_chrom(i, V+j) < z_star(j)
            z_star(j) = pop_chrom(i, V+j);
        end
    end
end

dist_matrix = pdist2(lambda, lambda);
[~, neighbors] = sort(dist_matrix, 2);
B = neighbors(:, 1:T);

for g = 1:gen
    for i = 1:pop
        nbrs = B(i, :);
        k = nbrs(randi(T));
        l = nbrs(randi(T));
        while l == k
            l = nbrs(randi(T));
        end

        y = pop_chrom(i, 1:V);
        F = 0.5;
        CR = 0.9;
        for j = 1:V
            if rand() < CR
                y(j) = pop_chrom(i, j) + F * (pop_chrom(k, j) - pop_chrom(l, j));
            end
        end
        y = max(min(y, max_range), min_range);

        y_obj = evaluate_objective(y, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
        y_full = [y, y_obj];

        for j = 1:M
            if y_obj(j) < z_star(j)
                z_star(j) = y_obj(j);
            end
        end

        n_updated = 0;
        max_update = 2;
        for ni = 1:T
            if n_updated >= max_update, break; end
            n_idx = B(i, ni);
            g_old = max(lambda(n_idx, :) .* abs(pop_chrom(n_idx, V+1:V+M) - z_star));
            g_new = max(lambda(n_idx, :) .* abs(y_obj - z_star));
            if g_new <= g_old
                pop_chrom(n_idx, :) = y_full;
                n_updated = n_updated + 1;
            end
        end
    end

    if ~mod(g, 100)
        clc
        fprintf('MOEA/D-DE: %d/%d generations\n', g, gen);
    end
end

chromosome = non_domination_sort_mod(pop_chrom, M, V);
end

function W = generate_weight_vectors(N, M)
    if M == 2
        W = zeros(N, M);
        for i = 1:N
            W(i, 1) = (i - 1) / (N - 1);
            W(i, 2) = 1 - W(i, 1);
        end
    else
        W = rand(N, M);
        W = W ./ sum(W, 2);
    end
end