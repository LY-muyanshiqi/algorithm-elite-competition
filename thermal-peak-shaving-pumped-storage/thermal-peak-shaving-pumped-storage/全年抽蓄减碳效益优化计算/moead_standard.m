function chromosome = moead_standard(Nh, Nw, Np, L, Zpump, h, Cprice)
% MOEA/D   
%  NSLDE  evaluate_objective

pop = 100;
gen = 3000;
T = 20;  % 
[M, V, min_range, max_range] = objective_description_function();

% === 1.  (simplex-lattice, 2) ===
lambda = zeros(pop, M);
for i = 1:pop
    lambda(i, 1) = (i-1)/(pop-1);
    lambda(i, 2) = 1 - lambda(i, 1);
end

% === 2.  ===
B = zeros(pop, T);
for i = 1:pop
    dist = zeros(pop, 1);
    for j = 1:pop
        dist(j) = norm(lambda(i, :) - lambda(j, :));
    end
    [~, idx] = sort(dist);
    B(i, :) = idx(1:T);
end

% === 3.  ===
x = zeros(pop, V);
fx = zeros(pop, M);
for i = 1:pop
    for j = 1:V
        x(i, j) = min_range(j) + (max_range(j) - min_range(j)) * rand(1);
    end
    obj = evaluate_objective(x(i,:), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    fx(i, :) = obj;
end

% === 4.  ===
z_star = min(fx, [], 1);

% === 5.  ===
for g = 1:gen
    for i = 1:pop
        % 
        nbrs = B(i, :);
        p1_idx = nbrs(randi(T));
        p2_idx = nbrs(randi(T));
        while p1_idx == p2_idx
            p2_idx = nbrs(randi(T));
        end

        % DE/rand/1  (F=0.65) +  (pm=1/V, mum=20)
        y = zeros(1, V);
        for j = 1:V
            if rand(1) < 0.7
                y(j) = x(i, j) + 0.65 * (x(p1_idx, j) - x(p2_idx, j));
            else
                y(j) = x(i, j);
            end
            r = rand(1);
            if r < 1/V
                if r < 0.5
                    delta = (2*r)^(1/21) - 1;
                else
                    delta = 1 - (2*(1-r))^(1/21);
                end
                y(j) = y(j) + delta * (max_range(j) - min_range(j));
            end
            if y(j) > max_range(j), y(j) = max_range(j); end
            if y(j) < min_range(j), y(j) = min_range(j); end
        end

        fy = evaluate_objective(y, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);

        % 
        for k = 1:M
            if fy(k) < z_star(k), z_star(k) = fy(k); end
        end

        % 
        for j_idx = 1:T
            j = nbrs(j_idx);
            g_old = max(lambda(j, :) .* (fx(j, :) - z_star));
            g_new = max(lambda(j, :) .* (fy - z_star));
            if g_new <= g_old
                x(j, :) = y;
                fx(j, :) = fy;
            end
        end
    end

    if ~mod(g, 100)
        clc
        fprintf('%d generations completed (MOEA/D)\n', g);
    end
end

% === 6.  ===
chromosome = [x, fx];
chromosome = non_domination_sort_mod(chromosome, M, V);
end
