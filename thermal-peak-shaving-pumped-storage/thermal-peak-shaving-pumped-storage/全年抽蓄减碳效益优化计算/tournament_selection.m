function f = tournament_selection(chromosome, pool_size, tour_size)

%% function tournament_selection(chromosome, pool_size, tour_size) 
% is the selection policy for selecting the individuals for the mating 
% pool. The selection is based on tournament selection. Argument 
% |chromosome| is the current generation population from which the 
% individuals are selected to form a mating pool of size |pool_size| after 
% performing tournament selection, with size of the tournament being 
% |tour_size|. By varying the tournament size the selection pressure can be
% adjusted. But for NSGA-II the tour_size is fixed to two, but the user may
% feel free to experiment with different tournament size. Also it has been
% observed that a tournament size of more than five has no significant
% meaning. 
%
%% Tournament selection process
% In a tournament selection process n individuals are selected at random,
% where n is equal to |tour_size|. From these individuals only one is selected
% and is added to the mating pool, where size of the mating pool is
% |pool_size|. Selection is performed based on two criteria. First and
% foremost is the rank or the front in which the solutions reside.
% Individuals with lower rank are selected. Secondly if the rank of two
% individuals are the same then, the crowding distance is compared.
% Individuals with greater crowding distance is selcted. 

% Get the size of chromosome. The number of chromosome is not important
% while the number of elements in chromosome are important.
[pop, variables] = size(chromosome);
% The peunltimate element contains the information about rank.
rank = variables - 1;
% The last element contains information about crowding distance.
distance = variables;

% Until the mating pool is filled, perform tournament selection
for i = 1 : pool_size
    % Select n individuals at random, where n = tour_size
    for j = 1 : tour_size
        % Select an individual at random (with safety cap on retries)
        candidate(j) = 1 + floor(pop * rand(1));
        if candidate(j) > pop, candidate(j) = pop; end
        if candidate(j) < 1, candidate(j) = 1; end
        if j > 1
            % Make sure that same candidate is not chosen (cap retries)
            retry = 0;
            while ~isempty(find(candidate(1 : j - 1) == candidate(j))) && retry < 100
                candidate(j) = 1 + floor(pop * rand(1));
                if candidate(j) > pop, candidate(j) = pop; end
                if candidate(j) < 1, candidate(j) = 1; end
                retry = retry + 1;
            end
        end
    end
    % Collect information about the selected candidates.
    for j = 1 : tour_size
        c_obj_rank(j) = chromosome(candidate(j),rank);
        c_obj_distance(j) = chromosome(candidate(j),distance);
    end
    % Find the candidate with the least rank 
    min_candidate = ...
        find(c_obj_rank == min(c_obj_rank));
    if isempty(min_candidate), min_candidate = 1; end
    % If more than one candiate have the least rank then find the candidate
    % within that group having the maximum crowding distance.
    if length(min_candidate) ~= 1  %length:
        max_candidate = ...
        find(c_obj_distance(min_candidate) == max(c_obj_distance(min_candidate)));
        % If no candidate found (all crowding distances equal/zero), pick first.
        if isempty(max_candidate)
            max_candidate = 1;
        end
        % If a few individuals have the least rank and have maximum crowding
        % distance, select only one individual (not at random). 
        if length(max_candidate) ~= 1
            max_candidate = max_candidate(1);
        end
        % Safety bounds before indexing
        mci = min_candidate(min(max_candidate, length(min_candidate)));
        mci = min(mci, length(candidate));
        % Add the selected individual to the mating pool
        f(i,:) = chromosome(candidate(mci),:);
    else
        mci = min(min_candidate(1), length(candidate));
        % Add the selected individual to the mating pool
        f(i,:) = chromosome(candidate(mci),:);
    end
end