function chromosome = nsga3_standard(Nh, Nw, Np, L, Zpump, h, Cprice, pop, gen)
% nsga3_standard -  NSGA-III 
%
%  NSGA-II 

if nargin < 8, pop = 100; end
if nargin < 9, gen = 200; end

[M, V, min_range, max_range] = objective_description_function();

n_ref = pop;
ref_points = generate_reference_points(M, n_ref);

chromosome = initialize_variables(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
chromosome = non_domination_sort_mod(chromosome, M, V);

for i = 1:gen
    pool = round(pop / 2);
    tour = 2;
    parent_chromosome = tournament_selection(chromosome, pool, tour);
    offspring_chromosome = genetic_operator(parent_chromosome, chromosome, M, V, ...
        min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);

    [main_pop, ~] = size(chromosome);
    [offspring_pop, ~] = size(offspring_chromosome);
    intermediate_chromosome(1:main_pop, :) = chromosome;
    intermediate_chromosome(main_pop+1:main_pop+offspring_pop, 1:M+V) = offspring_chromosome;

    intermediate_chromosome = non_domination_sort_mod(intermediate_chromosome, M, V);
    chromosome = nsga3_selection(intermediate_chromosome, M, V, pop, ref_points);

    if ~mod(i, 100)
        clc
        fprintf('NSGA-III: %d/%d generations\n', i, gen);
    end
end
end

function ref_pts = generate_reference_points(M, n_div)
    if M == 2
        ref_pts = zeros(n_div, 2);
        for i = 1:n_div
            ref_pts(i, 1) = (i - 1) / (n_div - 1);
            ref_pts(i, 2) = 1 - ref_pts(i, 1);
        end
    else
        ref_pts = rand(n_div, M);
        ref_pts = ref_pts ./ sum(ref_pts, 2);
    end
end

function new_pop = nsga3_selection(intermediate_chromosome, M, V, pop, ref_points)
    max_rank = max(intermediate_chromosome(:, V+M+1));

    new_pop = [];
    for r = 1:max_rank
        front = intermediate_chromosome(intermediate_chromosome(:, V+M+1) == r, :);
        if size(new_pop, 1) + size(front, 1) <= pop
            new_pop = [new_pop; front];
        else
            n_need = pop - size(new_pop, 1);
            obj_vals = front(:, V+1:V+M);

            obj_min = min(obj_vals);
            obj_max = max(obj_vals);
            if all(obj_max - obj_min > 0)
                obj_norm = (obj_vals - obj_min) ./ (obj_max - obj_min);
            else
                obj_norm = obj_vals;
            end

            distances = pdist2(obj_norm, ref_points);
            [min_dist, assoc] = min(distances, [], 2);

            rho = zeros(1, size(ref_points, 1));
            for j = 1:size(new_pop, 1)
                obj_j = new_pop(j, V+1:V+M);
                if all(obj_max - obj_min > 0)
                    obj_j_norm = (obj_j - obj_min) ./ (obj_max - obj_min);
                else
                    obj_j_norm = obj_j;
                end
                [~, assoc_j] = min(pdist2(obj_j_norm, ref_points));
                rho(assoc_j) = rho(assoc_j) + 1;
            end

            selected = zeros(n_need, size(front, 2));
            sel_count = 0;
            while sel_count < n_need
                [~, ref_idx] = min(rho);
                candidates = find(assoc == ref_idx);
                if isempty(candidates)
                    rho(ref_idx) = inf;
                    continue;
                end
                [~, best_in] = min(min_dist(candidates));
                chosen = candidates(best_in);
                selected(sel_count + 1, :) = front(chosen, :);
                sel_count = sel_count + 1;
                rho(ref_idx) = rho(ref_idx) + 1;
                assoc(chosen) = 0;
            end
            new_pop = [new_pop; selected];
            break;
        end
    end

    if size(new_pop, 1) < pop
        remaining = pop - size(new_pop, 1);
        unused = intermediate_chromosome(~ismember(intermediate_chromosome(:, 1:V), new_pop(:, 1:V), 'rows'), :);
        if size(unused, 1) >= remaining
            new_pop = [new_pop; unused(1:remaining, :)];
        end
    end
end