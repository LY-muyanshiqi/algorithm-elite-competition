
function f = non_domination_sort_mod(x, M, V)

%% function f = non_domination_sort_mod(x, M, V)  ��֧������
% This function sort the current popultion based on non-domination. All the���ֹ��ܸ��ݷ�֧���ԶԵ�ǰ��Ⱥ�������� 
% individuals in the first front are given a rank of 1, the second front   �����ڵ�һ�ȼ�����Ա�������1�����������ڶ����ȼ��ĸ��˱�������2����
% individuals are assigned rank 2 and so on. After assigning the rank the  �������ơ� ���������󣬼���ÿ��ǰ���е�ӵ���ȡ�
% crowding in each front is calculated.

[N, m] = size(x);  %size����ȡ���������������
clear m  %���m

% Initialize the front number to 1.  ��ʼ��ǰ�εȼ�Ϊ1
front = 1;

% There is nothing to this assignment, used only to manipulate easily in
% MATLAB.
F(front).f = [];
individual = [];

%% Non-Dominated sort. ��֧������
% The initialized population is sorted based on non-domination. The fast   ��ʼ������Ⱥ�ǻ��ڷ�֧��������ġ� ���������㷨[1]��������
% sort algorithm [1] is described as below for each

% ?for each individual p in main population P do the following            ������Ҫ��ȺP�е�ÿ������p��ִ�����²���
%   ?Initialize Sp = []. This set would contain all the individuals that is  ��ʼ��Sp = []�� ������Ͻ�����������p�����ĸ��塣
%     being dominated by p.
%   ?Initialize np = 0. This would be the number of individuals that      ��ʼ��np = 0���⽫������p�ĸ���������
%   dominate p.
%            
%   ?for each individual q in P                                           ����P�е�ÿ������q
%       * if p dominated q then 
%           ?add q to the set Sp i.e. Sp = Sp ? {q}                       ���p֧��q����q�ӵ�����Sp
%       * else if q dominates p then                                        ���q֧��p
%           ?increment the domination counter for p i.e. np = np + 1      ����p��֧��������np = np + 1
%   ?if np = 0 i.e. no individuals dominate p then p belongs to the first ���np = 0����û�и�������p����p���ڵ�һ�ȼ�; 
%     front; Set rank of individual p to one i.e prank = 1. Update the first  ������p����������Ϊ1����prank= 1.
%     front set by adding p to front one i.e F1 = F1 ? {p}                 ͨ����p���ӵ�ǰһ�����ϣ���F1 = F1�����µ�һ��ǰ�˼��ϡ�{P}
% ?This is carried out for all the individuals in main population P.      ���������ҪP��Ⱥ�е����и�����еġ�
% ?Initialize the front counter to one. i = 1                             ��ʼ��front counter to one�� i = 1
% ?following is carried out while the ith front is nonempty i.e. Fi != [] �ڵ�i��ǰ���ǿյ�ʱ��ִ�����²�������Fi��= [] Q = []�� 
%   ?Q = []. The set for storing the individuals for (i + 1)th front.     ���ڴ洢��i + 1�����ĸ���ļ��ϡ�
%   ?for each individual p in front Fi                                    ����Fiǰ���ÿ������p
%       * for each individual q in Sp (Sp is the set of individuals        ����Sp�е�ÿ������q��Sp����p֧���һ����壩
%         dominated by p)
%           ?nq = nq+1, decrement the domination count for individual q.   nq = nq+1�����ٸ���q��֧����
%           ?if nq = 0 then none of the individuals in the subsequent     ���nq = 0����ô�ں�����κ�һ���嶼����֧��q��
%             fronts would dominate q. Hence set qrank = i + 1. Update      �������qrank = i + 1�� �ø���q���¼���Q
%             the set Q with individual q i.e. Q = Q ? q.                  ����Q = Q ? q
%   ?Increment the front counter by one.                                  ���߲������һ��
%   ?Now the set Q is the next front and hence Fi = Q.                    ���ڼ���Q����һ���ߵȼ������Fi = Q.
%
% This algorithm is better than the original NSGA ([2]) since it utilize   ���㷨��ԭ����NSGA��[2]�����ã�
% the informatoion about the set that an individual dominate (Sp) and      ��Ϊ�����ù��ڸ���֧�䣨Sp����֧����壨np���ĸ��������ļ��ϵ���Ϣ��
% number of individuals that dominate the individual (np).

%
for i = 1 : N     %��Ⱥѭ��
    % Number of individuals that dominate this individual   ֧���������ĸ�����
    individual(i).n = 0;
    % Individuals which this individual dominate            ���������֧��ĸ���
    individual(i).p = [];
    for j = 1 : N    %��Ⱥѭ��
        dom_less = 0;
        dom_equal = 0;
        dom_more = 0;
        for k = 1 : M   %Ŀ�꺯��ѭ��
            if (x(i,V + k) < x(j,V + k))  %�������i��kĿ���j��
                dom_less = dom_less + 1;
            elseif abs(x(i,V + k) - x(j,V + k)) < 1e-9   %�������i��kĿ���j��ͬ
                dom_equal = dom_equal + 1;
            else
                dom_more = dom_more + 1;    %�������i��kĿ���j��
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
% Find the subsequent fronts  �ҵ�������
while ~isempty(F(front).f) % �� isempty �����Ϊ��ȡ0 ��Ϊ��ȡ1
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