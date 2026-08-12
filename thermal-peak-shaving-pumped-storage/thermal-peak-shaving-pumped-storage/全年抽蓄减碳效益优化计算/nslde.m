function chromosome = nslde(Nh, Nw, Np, L, Zpump, h, Cprice, pop, gen)

if nargin < 8, pop = 100; end
if nargin < 9, gen = 3000; end
[M, V, min_range, max_range] = objective_description_function();

chromosome = initialize_variables(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
chromosome = non_domination_sort_mod(chromosome, M, V);

%% Start the evolution process                                    ��ʼ��������
% The following are performed in each generation                           ������ÿһ��ִ�еĲ���
% * Select the parents which are fit for reproduction                      ѡ���ʺϷ�ֳ�ĸ���
% * Perfrom crossover and Mutation operator on the selected parents        ����ѡ����������ִ�н����ͻ�����
% * Perform Selection from the parents and the offsprings                  �ڸ������Ӵ�֮�����ѡ�����
% * Replace the unfit individuals with the fit individuals to maintain a
%   constant population size.                                              �ú��ʵĸ����滻�����ʵĸ��壬�Ա��ֺ㶨����Ⱥ��ģ��

for i = 1 : gen
    pool = round(pop / 2);
    tour = 2;
    parent_chromosome = tournament_selection(chromosome, pool, tour);
    offspring_chromosome = genetic_operator(parent_chromosome, chromosome, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);

    chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);
    if ~mod(i, 100)
        clc
        fprintf('%d generations completed\n', i);
    end
end

    
