function chromosome=nslde(Nh,Nw,Np,L,Zpump,h,Cprice)
%if nargin < 2  %�жϱ�������
%    error('NSGA-II: Please enter the population size and number of generations as input arguments.');%��������Ⱥ��С��������������Ϊ����
%end
% Both the input arguments need to of integer data type ����
%if isnumeric(pop) == 0 || isnumeric(gen) == 0   %isnumeric���ж���������Ƿ����������ͣ����������ͺ����ͣ�
                                                %����1��true�����A���������͵ģ�
                                                %����0��false�����A�����������͵�.���͵�
%    error('Both input arguments pop and gen should be integer datatype');
%end
% Minimum population size has to be 20 individuals  ��Ⱥ��С��СΪ20


%if pop < 20
%    error('Minimum population for running this function is 20');
%end
%if gen < 5
%    error('Minimum number of generations is 5');
%end
% Make sure pop and gen are integers��������
pop = round(100);   %round����������ȡ��
gen = round(3000);
%% Objective Function   Ŀ�꺯��
% The objective function description contains information about the        Ŀ�꺯�����������й�Ŀ�꺯������Ϣ�� M��Ŀ��ռ��ά����V�Ǿ��߱����ռ��ά����                                                                           
% objective function. M is the dimension of the objective space, V is the  min_range��max_range�Ǿ��߱����ռ��б����ķ�Χ�� ��
% dimension of decision variable space, min_range and max_range are the    �û�����ʹ�þ��߱�������Ŀ�꺯���� 
% range for the variables in the decision variable space. User has to      ȷ���༭������evaluate_objective��������������Ҫ
% define the objective functions using the decision variables. Make sure to
% edit the function 'evaluate_objective' to suit your needs.
[M, V, min_range, max_range] = objective_description_function();  %Ŀ������

%% Initialize the population   ��Ⱥ��ʼ��
% Population is initialized with random values which are within the        ��ָ����Χ�ڶ���Ⱥ���г�ʼ���� 
% specified range. Each chromosome consists of the decision variables. Alsoÿ��Ⱦɫ���ɾ��߱�����ɡ� 
% the value of the objective functions, rank and crowding distance         ���⣬Ŀ�꺯�����ȼ���ӵ��������Ϣ��ֵҲ�����ӵ�Ⱦɫ�������У�
% information is also added to the chromosome vector but only the elements ����ֻ�о��о��߱�����������Ԫ�ر�������ִ����corssover��ͻ����Ŵ�������
% of the vector which has the decision variables are operated upon to
% perform the genetic operations like corssover and mutation.
chromosome = initialize_variables(pop, M, V, min_range, max_range,Nh,Nw,Np,L,Zpump,h,Cprice);


%% Sort the initialized population   ��ʼ����Ⱥ����
% Sort the population using non-domination-sort. This returns two columns  ʹ�÷�֧���������Ⱥ�������� 
% for each individual which are the rank and the crowding distance         ��Ϊÿ�����巵�����У���Щ���Ƕ�Ӧ��������ǰ�˵�λ�õ�������ӵ�����롣 
% corresponding to their position in the front they belong. At this stage  ������׶Σ�ÿ��Ⱦɫ��������ӵ�����뱻���ӵ�Ⱦɫ���������Ա��ڼ��㡣
% the rank and the crowding distance for each chromosome is added to the
% chromosome vector for easy of computation.
chromosome = non_domination_sort_mod(chromosome, M, V);  %��֧������

%% Start the evolution process                                    ��ʼ��������
% The following are performed in each generation                           ������ÿһ��ִ�еĲ���
% * Select the parents which are fit for reproduction                      ѡ���ʺϷ�ֳ�ĸ���
% * Perfrom crossover and Mutation operator on the selected parents        ����ѡ����������ִ�н����ͻ�����
% * Perform Selection from the parents and the offsprings                  �ڸ������Ӵ�֮�����ѡ�����
% * Replace the unfit individuals with the fit individuals to maintain a
%   constant population size.                                              �ú��ʵĸ����滻�����ʵĸ��壬�Ա��ֺ㶨����Ⱥ��ģ��

for i = 1 : gen
    % Select the parents ����������
    % Parents are selected for reproduction to generate offspring. The
    % �Ӹ��������������Ӵ�
    % original NSGA-II uses a binary tournament selection based on
    % the��ͳ��nsga2 ʹ����һ�ֻ���ӵ�������ӵĶ����ƽ���������
    % crowded-comparision operator. The arguments are ������
    % pool - size of the mating pool. It is common to have this to be half the
    %        population size.����صĴ�С����ͨ������Ⱥ��С��һ��
    % tour - Tournament size. Original NSGA-II uses a binary tournament
    %        selection, but to see the effect of tournament size this is kept
    %        arbitary, to be choosen by the user.
    pool = round(pop/2);
    tour = 2; 
    % Selection process ѡ�����
    % A binary tournament selection is employed in NSGA-II. In a binary(������)
    % tournament selection process two individuals are selected at random
    % and their fitness is compared. The individual with better fitness is
    % selcted as a parent. Tournament selection is carried out until the
    % pool size is filled. Basically a pool size is the number of parents
    % to be selected. The input arguments(����) to the function
    % tournament_selection are chromosome, pool, tour. The function uses
    % only the information from last two elements�����ӣ� in the chromosome vector�����壩.
    % The last element��Ԫ�أ� has the crowding distance information while the
    % penultimate element�������ڶ����� has the rank information. Selection is based on
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
        genetic_operator(parent_chromosome,chromosome, M, V, min_range, max_range,Nh,Nw,Np,L,Zpump,h,Cprice);

    % Intermediate population���м���壩
    % Intermediate population is the combined population of parents and
    % offsprings of the current generation. The population size is two
    % times the initial population���е��˿��ǵ�����ĸ����Ů�ĺϲ��˿ڡ� �˿ڹ�ģ�ǳ�ʼ�˿ڵ�������.
    
    [main_pop,temp] = size(chromosome);
    [offspring_pop,temp] = size(offspring_chromosome);
    % temp is a dummy variable�����������.
    clear temp
    % intermediate_chromosome is a concatenation of current population and
    % the offspring population.
    intermediate_chromosome(1:main_pop,:) = chromosome;
    intermediate_chromosome(main_pop + 1 : main_pop + offspring_pop,1 : M+V) = ...
        offspring_chromosome;

    % Non-domination-sort of intermediate population
    % The intermediate population is sorted again based on non-domination sort
    % before the replacement operator is performed on the intermediate
    % population���ڶ��м��˿ڽ����滻����Ա֮ǰ���м��˿��ٴλ��ڷ�֧��������з��ࡣ��.
    intermediate_chromosome = ...
        non_domination_sort_mod(intermediate_chromosome, M, V);
    % Perform Selection
    % Once the intermediate population is sorted only the best solution isһ���м���Ⱥ�����࣬�������ĵȼ���ӵ������ֻѡ����õĽ�������� 
    % selected based on it rank and crowding distance. Each front is filled inÿ��ǰ�ذ����������У�ֱ���ﵽ�˿ڹ�ģ�� 
    % ascending order until the addition of population size is reached. The���ݾ�����С����Ⱥ������ǰ�ذ������˿���
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

    
