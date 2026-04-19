function f  = genetic_operator(parent_chromosome, chromosome, M, V,  l_limit, u_limit,Nh,Nw,Np,L,Zpump,h)

%% function f  = genetic_operator(parent_chromosome, M, V, mu, mum, l_limit, u_limit)
% 
% This function is utilized(被用来) to produce offsprings from parent chromosomes.
% The genetic operators corssover and mutation which are carried out with
% slight modifications（轻微修改） from the original design. For more information read
% the document enclosed. 
%
% parent_chromosome - the set of selected chromosomes.
% M - number of objective functions
% V - number of decision varaiables
% mu - distribution index for crossover (read the enlcosed pdf file)
% mum - distribution index for mutation (read the enclosed pdf file)
% l_limit - a vector of lower limit for the corresponding decsion variables
% u_limit - a vector of upper limit for the corresponding decsion variables
%
% The genetic operation is performed only on the decision variables, that
% is the first V elements in the chromosome vector（载体）. 

[N,m] = size(parent_chromosome);

clear m
p = 1;
child=[];
for i = 1 : N
        child_1 = [];
        child_2 = [];
        % Select the first parent
        parent_1 = round(N*rand(1));
        if parent_1 < 1
            parent_1 = 1;
        end
        % Select the second parent
        parent_2 = round(N*rand(1));
        if parent_2 < 1
            parent_2 = 1;
        end
        % Make sure both the parents are not the same. 
        while isequal(parent_chromosome(parent_1,:),parent_chromosome(parent_2,:))
            parent_2 = round(N*rand(1));
            if parent_2 < 1
                parent_2 = 1;
            end
        end
        % Get the chromosome information for each randomnly selected 
        % parents
        parent_1 = parent_chromosome(parent_1,:);
        parent_2 = parent_chromosome(parent_2,:);
        u.string=normrnd(0,0.6966,1,V);
        v.string=normrnd(0,1,1,V);
        r.string=-1+2*rand(1,V);
        % Perform corssover for each decision variable in the chromosome.
        for j = 1 : V
            % Generate the jth element of first child
            if rand(1)<0.7
                child_1(j) = ...
                    parent_chromosome(i,j)+0.3*(parent_1(j)-parent_2(j));
            else
                child_1(j)= parent_chromosome(i,j);
            end
            
            if rand(1)<0.5
                child_2(j) = ...
                    child_1(j)+50*(u.string(1,j))/(abs(v.string(1,j)))^(1/1.5);
            else
                child_2(j) = ...
                    child_1(j)+50*r.string(1,j);
            end
            % Make sure that the generated element is within the
            % specified（确保子代的范围）
            % decision space else set it to the appropriate extrema.
            if child_1(j) > u_limit(j)
                child_1(j) = u_limit(j);
            elseif child_1(j) < l_limit(j)
                child_1(j) = l_limit(j);
            end
            if child_2(j) > u_limit(j)
                child_2(j) = u_limit(j);
            elseif child_2(j) < l_limit(j)
                child_2(j) = l_limit(j);
            end
        end
        % Evaluate the objective function for the offsprings and as before
        % concatenate the offspring chromosome with objective value.
        child_1(:,V + 1: M + V) = evaluate_objective(child_1, M, V,Nh,Nw,Np,L,Zpump,h);
        child_2(:,V + 1: M + V) = evaluate_objective(child_2, M, V,Nh,Nw,Np,L,Zpump,h);
        child(p,:) = child_1;
        child(p+1,:) = child_2;
        p = p + 2;

end

f = child;