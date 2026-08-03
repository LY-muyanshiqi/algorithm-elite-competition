function [number_of_objectives, number_of_decision_variables, min_range_of_decesion_variable, max_range_of_decesion_variable] = objective_description_function()
%目标个数，决策变量个数，决策变量最小值、最大值
%% function [number_of_objectives, number_of_decision_variables, min_range_of_decesion_variable, max_range_of_decesion_variable] = objective_description_function()
% This function is used to completely describe the objective functions and 此功能用于完全描述目标函数和决策变量空间等的范围。
% the range for the decision variable space etc. The user is prompted for  用户被提示输入目标数量，决策变量的数量，每个决策变量的最大和最小范围，
% inputing the number of objectives, numebr of decision variables, the     最后功能等待 供用户修改evaluate_objective功能以满足需要。
% maximum and minimum range for each decision variable and finally the
% function waits for the user to modify the evaluate_objective function to
% suit their need.

number_of_objectives = 2;
if number_of_objectives < 2
    error('This is a multi-objective optimization function hence the minimum number of objectives is two');%这是一个多目标优化函数，因此目标的最小数目是两个
end
number_of_decision_variables = 23;
for i = 1 :21
    %clc
    %g = sprintf('\nInput the minimum value for decision variable %d : ', i);
    % Obtain the minimum possible value for each decision variable   获取每个决策变量的最小可能值
    min_range_of_decesion_variable(i) = 0;
    g = sprintf('\nInput the maximum value for decision variable %d : ', i);
    % Obtain the maximum possible value for each decision variable   获取每个决策变量的最大可能值
    max_range_of_decesion_variable(i) = 1;
    %clc
end
 min_range_of_decesion_variable(22)=0.125;
 max_range_of_decesion_variable(22)=1;
 min_range_of_decesion_variable(23)=0.3125;
 max_range_of_decesion_variable(23)=0.75;
