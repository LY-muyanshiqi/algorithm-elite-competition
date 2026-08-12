function f  = replace_chromosome(intermediate_chromosome, M, V,pop)

[N, m] = size(intermediate_chromosome);

% Get the index for the population sort based on the rank
[temp,index] = sort(intermediate_chromosome(:,M + V + 1));
clear temp m

% Now sort the individuals based on the index
sorted_chromosome = intermediate_chromosome(index, :);

% Find the maximum rank in the current population
max_rank = max(intermediate_chromosome(:,M + V + 1));
if isempty(max_rank), max_rank = 1; end
if isnan(max_rank) || isinf(max_rank), max_rank = 1; end
max_rank = min(max_rank, N);

previous_index = 0;
f = [];
for i = 1 : max_rank
    % Last index of individuals with rank i
    idx_rank = find(sorted_chromosome(:,M + V + 1) == i);
    if isempty(idx_rank)
        continue; % rank i missing (hole) -> skip safely
    end
    current_index = max(idx_rank);

    if current_index > pop
        remaining = pop - previous_index;
        temp_pop = sorted_chromosome(previous_index + 1 : min(current_index, N), :);
        remaining = min(remaining, size(temp_pop, 1));
        if remaining > 0
            [~, temp_sort_index] = sort(temp_pop(:, M + V + 2),'descend');
            for j = 1 : remaining
                f(previous_index + j,:) = temp_pop(temp_sort_index(j),:);
            end
        end
        break;
    else
        f(previous_index + 1 : current_index, :) = ...
            sorted_chromosome(previous_index + 1 : current_index, :);
        previous_index = current_index;
        if current_index >= pop
            break;
        end
    end
end

% Fallback: ensure output is always defined
if isempty(f) || size(f,1) < pop
    take = min(pop, N);
    f = sorted_chromosome(1:take, :);
end
end