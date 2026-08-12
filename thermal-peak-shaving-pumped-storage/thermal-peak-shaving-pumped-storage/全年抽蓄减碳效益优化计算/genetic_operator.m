function f  = genetic_operator(parent_chromosome, chromosome, M, V,  l_limit, u_limit,Nh,Nw,Np,L,Zpump,h,Cprice)

%% function f  = genetic_operator(parent_chromosome, M, V, mu, mum, l_limit, u_limit)
% 
% The genetic operators corssover and mutation which are carried out with
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
        pc = 0.7;
        F = 0.3;
        alpha_levy = 0.5;
        beta_levy = 1.5;
        sigma_u = 0.6966;

        for j = 1 : V
            if rand(1) < pc
                child_1(j) = parent_chromosome(i,j) + F * (parent_1(j) - parent_2(j));
            else
                child_1(j) = parent_chromosome(i,j);
            end

            if rand(1) < 0.5
                child_2(j) = child_1(j) + alpha_levy * u.string(1,j) / (abs(v.string(1,j)))^(1/beta_levy);
            else
                child_2(j) = child_1(j) + alpha_levy * r.string(1,j);
            end

            child_1(j) = reflect_bounds(child_1(j), l_limit(j), u_limit(j));
            child_2(j) = reflect_bounds(child_2(j), l_limit(j), u_limit(j));
        end
        % Evaluate the objective function for the offsprings and as before
        % concatenate the offspring chromosome with objective value.
        child_1(:,V + 1: M + V) = evaluate_objective(child_1, M, V,Nh,Nw,Np,L,Zpump,h,Cprice);
        child_2(:,V + 1: M + V) = evaluate_objective(child_2, M, V,Nh,Nw,Np,L,Zpump,h,Cprice);
        child(p,:) = child_1;
        child(p+1,:) = child_2;
        p = p + 2;

end

f = child;

function x = reflect_bounds(x, lb, ub)
    while x > ub || x < lb
        if x > ub
            x = 2 * ub - x;
        elseif x < lb
            x = 2 * lb - x;
        end
    end
end