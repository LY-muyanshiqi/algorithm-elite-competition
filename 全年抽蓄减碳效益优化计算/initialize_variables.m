function f = initialize_variables(N, M, V, min_range, max_range,Nh,Nw,Np,L,Zpump,h)

%% function f = initialize_variables(N, M, V, min_tange, max_range) 
% This function initializes the chromosomes. Each chromosome has the
% following at this stage       初始化染色体
%       * set of decision variables   一组决策变量
%       * objective function values   目标函数值
% 
% where,
% N - Population size   种群大小
% M - Number of objective functions  目标函数个数
% V - Number of decision variables   决策变量个数
% min_range - A vector of decimal values which indicate the minimum value
% for each decision variable.  指示每个决策变量的最小值的十进制值向量
% max_range - Vector of maximum possible values for decision variables. 

min = min_range;
max = max_range;

% K is the total number of array elements. For ease of computation decision K是数组元素的总数。 
% variables and objective functions are concatenated to form a single      为了便于计算，决策变量和目标函数被连接形成单个数组。 
% array. For crossover and mutation only the decision variables are used   对于交叉和变异，仅使用决策变量进行选择，仅使用客观变量
% while for selection, only the objective variable are utilized.

K = M + V;
%% Initialize each chromosome
% For each chromosome perform the following (N is the population size)
y=[];
y(1,:)=rand(1,V);
for k= 1 : N
    for l = 1 : V
        y(k+1,l)=y(k,l)*4*(1-y(k,l));
    end
end
% For each chromosome perform the following (N is the population size)
for i = 1 : N
    % Initialize the decision variables based on the minimum and maximum   根据最小和最大可能值初始化决策变量。 
    % possible values. V is the number of decision variable. A random      V是决策变量的数量。 在每个决策变量的最小和最大可能值之间挑选一个随机数。
    % number is picked between the minimum and maximum possible values for
    % the each decision variable.
    
    for j = 1 : V
            f(i,j) = min(j) + (max(j) - min(j))*y(i+1,j);
    end
    % For ease of computation and handling data the chromosome also has the为了便于计算和处理数据，染色体末端还具有目标函数值。
    % vlaue of the objective function concatenated at the end. The elements元件V + 1至K具有目标函数的值。 
    % V + 1 to K has the objective function valued.                        函数evaluate_objective在一个时间只需一个染色体， 
    % The function evaluate_objective takes one chromosome at a time,      只有决策变量与被处理的目标函数的数量一起传递给函数，并返回目标函数的值。
    % infact only the decision variables are passed to the function along  这些值现在存储在染色体本身的末端。
    % with information about the number of objective functions which are
    % processed and returns the value for the objective functions. These
    % values are now stored at the end of the chromosome itself.
    f(i,V + 1: K) = evaluate_objective(f(i,:), M, V,Nh,Nw,Np,L,Zpump,h);   %计算目标函数
end