
function f = non_domination_sort_mod(x, M, V)

%% function f = non_domination_sort_mod(x, M, V)  非支配排序
% This function sort the current popultion based on non-domination. All the这种功能根据非支配性对当前种群进行排序。 
% individuals in the first front are given a rank of 1, the second front   所有在第一等级的人员都获得了1级的排名，第二名等级的个人被分配了2级，
% individuals are assigned rank 2 and so on. After assigning the rank the  依此类推。 分配排名后，计算每个前排中的拥挤度。
% crowding in each front is calculated.

[N, m] = size(x);  %size：获取矩阵的行数和列数
clear m  %清除m

% Initialize the front number to 1.  初始化前段等级为1
front = 1;

% There is nothing to this assignment, used only to manipulate easily in
% MATLAB.
F(front).f = [];
individual = [];

%% Non-Dominated sort. 非支配排序
% The initialized population is sorted based on non-domination. The fast   初始化的种群是基于非支配性排序的。 快速排序算法[1]如下所述
% sort algorithm [1] is described as below for each

% ?for each individual p in main population P do the following            对于主要种群P中的每个个体p，执行以下操作
%   ?Initialize Sp = []. This set would contain all the individuals that is  初始化Sp = []。 这个集合将包含所有由p主导的个体。
%     being dominated by p.
%   ?Initialize np = 0. This would be the number of individuals that      初始化np = 0。这将是主导p的个体数量。
%   dominate p.
%            
%   ?for each individual q in P                                           对于P中的每个个体q
%       * if p dominated q then 
%           ?add q to the set Sp i.e. Sp = Sp ? {q}                       如果p支配q，则将q加到集合Sp
%       * else if q dominates p then                                        如果q支配p
%           ?increment the domination counter for p i.e. np = np + 1      增加p的支配数，即np = np + 1
%   ?if np = 0 i.e. no individuals dominate p then p belongs to the first 如果np = 0，则没有个体主导p，则p属于第一等级; 
%     front; Set rank of individual p to one i.e prank = 1. Update the first  将个体p的排名设置为1，即prank= 1.
%     front set by adding p to front one i.e F1 = F1 ? {p}                 通过将p添加到前一个集合，即F1 = F1来更新第一个前端集合。{P}
% ?This is carried out for all the individuals in main population P.      这是针对主要P种群中的所有个体进行的。
% ?Initialize the front counter to one. i = 1                             初始化front counter to one。 i = 1
% ?following is carried out while the ith front is nonempty i.e. Fi != [] 在第i个前面是空的时候执行以下操作，即Fi！= [] Q = []。 
%   ?Q = []. The set for storing the individuals for (i + 1)th front.     用于存储（i + 1）个的个体的集合。
%   ?for each individual p in front Fi                                    对于Fi前面的每个个体p
%       * for each individual q in Sp (Sp is the set of individuals        对于Sp中的每个个体q（Sp是由p支配的一组个体）
%         dominated by p)
%           ?nq = nq+1, decrement the domination count for individual q.   nq = nq+1，减少个体q的支配数
%           ?if nq = 0 then none of the individuals in the subsequent     如果nq = 0，那么在后面的任何一个体都不会支配q。
%             fronts would dominate q. Hence set qrank = i + 1. Update      因此设置qrank = i + 1。 用个体q更新集合Q
%             the set Q with individual q i.e. Q = Q ? q.                  即：Q = Q ? q
%   ?Increment the front counter by one.                                  将高层次增加一个
%   ?Now the set Q is the next front and hence Fi = Q.                    现在集合Q是下一个高等级，因此Fi = Q.
%
% This algorithm is better than the original NSGA ([2]) since it utilize   该算法比原来的NSGA（[2]）更好，
% the informatoion about the set that an individual dominate (Sp) and      因为它利用关于个体支配（Sp）和支配个体（np）的个体数量的集合的信息，
% number of individuals that dominate the individual (np).

%
for i = 1 : N     %种群循环
    % Number of individuals that dominate this individual   支配这个个体的个体数
    individual(i).n = 0;
    % Individuals which this individual dominate            被这个个体支配的个体
    individual(i).p = [];
    for j = 1 : N    %种群循环
        dom_less = 0;
        dom_equal = 0;
        dom_more = 0;
        for k = 1 : M   %目标函数循环
            if (x(i,V + k) < x(j,V + k))  %如果个体i的k目标比j好
                dom_less = dom_less + 1;
            elseif (x(i,V + k) == x(j,V + k))   %如果个体i的k目标和j相同
                dom_equal = dom_equal + 1;
            else
                dom_more = dom_more + 1;    %如果个体i的k目标比j差
            end
        end
        if dom_less == 0 && dom_equal ~= M
            individual(i).n = individual(i).n + 1;
        elseif dom_more == 0 && dom_equal ~= M
            individual(i).p = [individual(i).p j];
        end
    end   
    if individual(i).n == 0
        x(i,M + V + 1) = 1;
        F(front).f = [F(front).f i];
    end
end
% Find the subsequent fronts  找到后续的
while ~isempty(F(front).f) % 反 isempty ：结果为空取0 不为空取1
   Q = [];
   for i = 1 : length(F(front).f)
       if ~isempty(individual(F(front).f(i)).p)
        	for j = 1 : length(individual(F(front).f(i)).p)
            	individual(individual(F(front).f(i)).p(j)).n = ...
                	individual(individual(F(front).f(i)).p(j)).n - 1;
        	   	if individual(individual(F(front).f(i)).p(j)).n == 0
               		x(individual(F(front).f(i)).p(j),M + V + 1) = ...
                        front + 1;
                    Q = [Q individual(F(front).f(i)).p(j)];
                end
            end
       end
   end
   front =  front + 1;
   F(front).f = Q;
end

[temp,index_of_fronts] = sort(x(:,M + V + 1));
for i = 1 : length(index_of_fronts)
    sorted_based_on_front(i,:) = x(index_of_fronts(i),:);
end
current_index = 0;

%% Crowding distance
%The crowing distance is calculated as below
% ?For each front Fi, n is the number of individuals.
%   ?initialize the distance to be zero for all the individuals i.e. Fi(dj ) = 0,
%     where j corresponds to the jth individual in front Fi.
%   ?for each objective function m
%       * Sort the individuals in front Fi based on objective m i.e. I =
%         sort(Fi,m).
%       * Assign infinite distance to boundary values for each individual
%         in Fi i.e. I(d1) = ? and I(dn) = ?
%       * for k = 2 to (n ? 1)
%           ?I(dk) = I(dk) + (I(k + 1).m ? I(k ? 1).m)/fmax(m) - fmin(m)
%           ?I(k).m is the value of the mth objective function of the kth
%             individual in I

% Find the crowding distance for each individual in each front
for front = 1 : (length(F) - 1)
%    objective = [];
    distance = 0;
    y = [];
    previous_index = current_index + 1;
    for i = 1 : length(F(front).f)
        y(i,:) = sorted_based_on_front(current_index + i,:);
    end
    current_index = current_index + i;
    % Sort each individual based on the objective
    sorted_based_on_objective = [];
    for i = 1 : M
        [sorted_based_on_objective, index_of_objectives] = ...
            sort(y(:,V + i));
        sorted_based_on_objective = [];
        for j = 1 : length(index_of_objectives)
            sorted_based_on_objective(j,:) = y(index_of_objectives(j),:);
        end
        f_max = ...
            sorted_based_on_objective(length(index_of_objectives), V + i);
        f_min = sorted_based_on_objective(1, V + i);
        y(index_of_objectives(length(index_of_objectives)),M + V + 1 + i)...
            = Inf;
        y(index_of_objectives(1),M + V + 1 + i) = Inf;
         for j = 2 : length(index_of_objectives) - 1
            next_obj  = sorted_based_on_objective(j + 1,V + i);
            previous_obj  = sorted_based_on_objective(j - 1,V + i);
            if (f_max - f_min == 0)
                y(index_of_objectives(j),M + V + 1 + i) = Inf;
            else
                y(index_of_objectives(j),M + V + 1 + i) = ...
                     (next_obj - previous_obj)/(f_max - f_min);
            end
         end
    end
    distance = [];
    distance(:,1) = zeros(length(F(front).f),1);
    for i = 1 : M
        distance(:,1) = distance(:,1) + y(:,M + V + 1 + i);
    end
    y(:,M + V + 2) = distance;
    y = y(:,1 : M + V + 2);
    z(previous_index:current_index,:) = y;
end
f = z();

%% References
% [1] *Kalyanmoy Deb, Amrit Pratap, Sameer Agarwal, and T. Meyarivan*, |A Fast
% Elitist Multiobjective Genetic Algorithm: NSGA-II|, IEEE Transactions on 
% Evolutionary Computation 6 (2002), no. 2, 182 ~ 197.
%
% [2] *N. Srinivas and Kalyanmoy Deb*, |Multiobjective Optimization Using 
% Nondominated Sorting in Genetic Algorithms|, Evolutionary Computation 2 
% (1994), no. 3, 221 ~ 248.