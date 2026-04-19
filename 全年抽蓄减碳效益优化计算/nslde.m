function chromosome=nslde(Nh,Nw,Np,L,Zpump,h)
%if nargin < 2  %判断变量个数
%    error('NSGA-II: Please enter the population size and number of generations as input arguments.');%请输入种群大小和最大迭代次数作为参数
%end
% Both the input arguments need to of integer data type 整数
%if isnumeric(pop) == 0 || isnumeric(gen) == 0   %isnumeric：判断输入参数是否是数字类型（包括浮点型和整型）
                                                %返回1（true）如果A是数字类型的，
                                                %返回0（false）如果A不是数字类型的.类型的
%    error('Both input arguments pop and gen should be integer datatype');
%end
% Minimum population size has to be 20 individuals  种群大小最小为20


%if pop < 20
%    error('Minimum population for running this function is 20');
%end
%if gen < 5
%    error('Minimum number of generations is 5');
%end
% Make sure pop and gen are integers（整数）
pop = round(100);   %round：四舍五入取整
gen = round(3000);
%% Objective Function   目标函数
% The objective function description contains information about the        目标函数描述包含有关目标函数的信息。 M是目标空间的维数，V是决策变量空间的维数，                                                                           
% objective function. M is the dimension of the objective space, V is the  min_range和max_range是决策变量空间中变量的范围。 。
% dimension of decision variable space, min_range and max_range are the    用户必须使用决策变量定义目标函数。 
% range for the variables in the decision variable space. User has to      确保编辑函数“evaluate_objective”以满足您的需要
% define the objective functions using the decision variables. Make sure to
% edit the function 'evaluate_objective' to suit your needs.
[M, V, min_range, max_range] = objective_description_function();  %目标描述

%% Initialize the population   种群初始化
% Population is initialized with random values which are within the        在指定范围内对种群进行初始化。 
% specified range. Each chromosome consists of the decision variables. Also每个染色体由决策变量组成。 
% the value of the objective functions, rank and crowding distance         此外，目标函数，等级和拥挤距离信息的值也被添加到染色体载体中，
% information is also added to the chromosome vector but only the elements 但是只有具有决策变量的向量的元素被操作以执行如corssover和突变的遗传操作。
% of the vector which has the decision variables are operated upon to
% perform the genetic operations like corssover and mutation.
chromosome = initialize_variables(pop, M, V, min_range, max_range,Nh,Nw,Np,L,Zpump,h);


%% Sort the initialized population   初始化种群排序
% Sort the population using non-domination-sort. This returns two columns  使用非支配排序对种群进行排序。 
% for each individual which are the rank and the crowding distance         这为每个个体返回两列，这些列是对应于其所属前端的位置的排名和拥挤距离。 
% corresponding to their position in the front they belong. At this stage  在这个阶段，每个染色体的排序和拥挤距离被添加到染色体载体中以便于计算。
% the rank and the crowding distance for each chromosome is added to the
% chromosome vector for easy of computation.
chromosome = non_domination_sort_mod(chromosome, M, V);  %非支配排序

%% Start the evolution process                                    开始进化过程
% The following are performed in each generation                           以下是每一代执行的操作
% * Select the parents which are fit for reproduction                      选择适合繁殖的父代
% * Perfrom crossover and Mutation operator on the selected parents        在所选父代个体上执行交叉和突变操作
% * Perform Selection from the parents and the offsprings                  在父代和子代之间进行选择操作
% * Replace the unfit individuals with the fit individuals to maintain a
%   constant population size.                                              用合适的个人替换不合适的个体，以保持恒定的种群规模。

for i = 1 : gen
    % Select the parents 父代中搜索
    % Parents are selected for reproduction to generate offspring. The
    % 从父代中搜索产生子代
    % original NSGA-II uses a binary tournament selection based on
    % the传统的nsga2 使用了一种基于拥挤度算子的二进制锦标赛机制
    % crowded-comparision operator. The arguments are 参数是
    % pool - size of the mating pool. It is common to have this to be half the
    %        population size.交配池的大小，这通常是种群大小的一半
    % tour - Tournament size. Original NSGA-II uses a binary tournament
    %        selection, but to see the effect of tournament size this is kept
    %        arbitary, to be choosen by the user.
    pool = round(pop/2);
    tour = 2; 
    % Selection process 选择过程
    % A binary tournament selection is employed in NSGA-II. In a binary(二进制)
    % tournament selection process two individuals are selected at random
    % and their fitness is compared. The individual with better fitness is
    % selcted as a parent. Tournament selection is carried out until the
    % pool size is filled. Basically a pool size is the number of parents
    % to be selected. The input arguments(参数) to the function
    % tournament_selection are chromosome, pool, tour. The function uses
    % only the information from last two elements（分子） in the chromosome vector（载体）.
    % The last element（元素） has the crowding distance information while the
    % penultimate element（倒数第二个） has the rank information. Selection is based on
    % rank and if individuals with same rank are encountered, crowding
    % distance is compared. A lower rank and higher crowding distance is
    % the selection criteria.
    parent_chromosome = tournament_selection(chromosome, pool, tour);
    %parent_chromosome=chromosome;
    
    % Perfrom crossover and Mutation operator
    % The original NSGA-II algorithm uses Simulated Binary Crossover (SBX) and
    % Polynomial  mutation. Crossover probability pc = 0.9 and mutation
    % probability is pm = 1/n, where n is the number of decision variables.
    % Both real-coded GA and binary-coded GA are implemented in the original
    % algorithm, while in this program only the real-coded GA is considered.
    % The distribution indeices for crossover and mutation operators as mu = 20
    % and mum = 20 respectively.
    %mu = 20;
    %mum = 20;
    offspring_chromosome = ...
        genetic_operator(parent_chromosome,chromosome, ...
        M, V,  min_range , max_range,Nh,Nw,Np,L,Zpump,h);

    % Intermediate population（中间个体）
    % Intermediate population is the combined population of parents and
    % offsprings of the current generation. The population size is two
    % times the initial population（中等人口是当代父母和子女的合并人口。 人口规模是初始人口的两倍）.
    
    [main_pop,temp] = size(chromosome);
    [offspring_pop,temp] = size(offspring_chromosome);
    % temp is a dummy variable（虚拟变量）.
    clear temp
    % intermediate_chromosome is a concatenation of current population and
    % the offspring population.
    intermediate_chromosome(1:main_pop,:) = chromosome;
    intermediate_chromosome(main_pop + 1 : main_pop + offspring_pop,1 : M+V) = ...
        offspring_chromosome;

    % Non-domination-sort of intermediate population
    % The intermediate population is sorted again based on non-domination sort
    % before the replacement operator is performed on the intermediate
    % population（在对中间人口进行替换操作员之前，中间人口再次基于非支配排序进行分类。）.
    intermediate_chromosome = ...
        non_domination_sort_mod(intermediate_chromosome, M, V);
    % Perform Selection
    % Once the intermediate population is sorted only the best solution is一旦中间种群被分类，根据它的等级和拥挤距离只选择最好的解决方案。 
    % selected based on it rank and crowding distance. Each front is filled in每个前沿按照升序排列，直到达到人口规模。 
    % ascending order until the addition of population size is reached. The根据距离最小的人群，最后的前沿包括在人口中
    % last front is included in the population based on the individuals with
    % least crowding distance
    chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);
    if ~mod(i,100)
        clc
        fprintf('%d generations completed\n',i);
    end
end

% %% Result
% % Save the result in ASCII text format.
% save solution.txt chromosome -ASCII
% %% Visualize
% % The following is used to visualize the result if objective space
% % dimension is visualizable.
% if M == 2
%     plot(chromosome(:,V + 1),chromosome(:,V + 2),'*');
% elseif M ==3
%     plot3(chromosome(:,V + 1),chromosome(:,V + 2),chromosome(:,V + 3),'*');
%     grid on
% end
% % best_num=compromise_solution(chromosome);
% % best_solution=chromosome(best_num,1:240);
% % save filename

    
