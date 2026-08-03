function f = initialize_variables(N, M, V, min_range, max_range,Nh,Nw,Np,L,Zpump,h,Cprice)

%% function f = initialize_variables(N, M, V, min_tange, max_range) 
% This function initializes the chromosomes. Each chromosome has the
% following at this stage       ��ʼ��Ⱦɫ��
%       * set of decision variables   һ����߱���
%       * objective function values   Ŀ�꺯��ֵ
% 
% where,
% N - Population size   ��Ⱥ��С
% M - Number of objective functions  Ŀ�꺯������
% V - Number of decision variables   ���߱�������
% min_range - A vector of decimal values which indicate the minimum value
% for each decision variable.  ָʾÿ�����߱�������Сֵ��ʮ����ֵ����
% max_range - Vector of maximum possible values for decision variables. 

min = min_range;
max = max_range;

% K is the total number of array elements. For ease of computation decision K������Ԫ�ص������� 
% variables and objective functions are concatenated to form a single      Ϊ�˱��ڼ��㣬���߱�����Ŀ�꺯���������γɵ������顣 
% array. For crossover and mutation only the decision variables are used   ���ڽ���ͱ��죬��ʹ�þ��߱�������ѡ�񣬽�ʹ�ÿ͹۱���
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
    % Initialize the decision variables based on the minimum and maximum   ������С��������ֵ��ʼ�����߱����� 
    % possible values. V is the number of decision variable. A random      V�Ǿ��߱����������� ��ÿ�����߱�������С��������ֵ֮����ѡһ���������
    % number is picked between the minimum and maximum possible values for
    % the each decision variable.
    
    for j = 1 : V
            f(i,j) = min(j) + (max(j) - min(j))*y(i+1,j);
    end
    % For ease of computation and handling data the chromosome also has theΪ�˱��ڼ���ʹ������ݣ�Ⱦɫ��ĩ�˻�����Ŀ�꺯��ֵ��
    % vlaue of the objective function concatenated at the end. The elementsԪ��V + 1��K����Ŀ�꺯����ֵ�� 
    % V + 1 to K has the objective function valued.                        ����evaluate_objective��һ��ʱ��ֻ��һ��Ⱦɫ�壬 
    % The function evaluate_objective takes one chromosome at a time,      ֻ�о��߱����뱻������Ŀ�꺯��������һ�𴫵ݸ�������������Ŀ�꺯����ֵ��
    % infact only the decision variables are passed to the function along  ��Щֵ���ڴ洢��Ⱦɫ�屾����ĩ�ˡ�
    % with information about the number of objective functions which are
    % processed and returns the value for the objective functions. These
    % values are now stored at the end of the chromosome itself.
    f(i,V + 1: K) = evaluate_objective(f(i,:), M, V,Nh,Nw,Np,L,Zpump,h,Cprice);   %����Ŀ�꺯��
end