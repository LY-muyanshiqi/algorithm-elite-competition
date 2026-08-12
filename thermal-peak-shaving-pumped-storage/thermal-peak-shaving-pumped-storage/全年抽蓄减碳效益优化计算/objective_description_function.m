function [number_of_objectives, number_of_decision_variables, min_range_of_decesion_variable, max_range_of_decesion_variable] = objective_description_function()
%
%% function [number_of_objectives, number_of_decision_variables, min_range_of_decesion_variable, max_range_of_decesion_variable] = objective_description_function()
% This function is used to completely describe the objective functions and 
% the range for the decision variable space etc. The user is prompted for  
% inputing the number of objectives, numebr of decision variables, the      evaluate_objective
% maximum and minimum range for each decision variable and finally the
% function waits for the user to modify the evaluate_objective function to
% suit their need.

number_of_objectives = 2;
if number_of_objectives < 2
    error('This is a multi-objective optimization function hence the minimum number of objectives is two');%
end
number_of_decision_variables = 23;
for i = 1 :21
    %clc
    %g = sprintf('\nInput the minimum value for decision variable %d : ', i);
    % Obtain the minimum possible value for each decision variable   
    min_range_of_decesion_variable(i) = 0;
    g = sprintf('\nInput the maximum value for decision variable %d : ', i);
    % Obtain the maximum possible value for each decision variable   
    max_range_of_decesion_variable(i) = 1;
    %clc
end
 min_range_of_decesion_variable(22)=0.125;
 max_range_of_decesion_variable(22)=1;
 min_range_of_decesion_variable(23)=0.3125;
 max_range_of_decesion_variable(23)=0.75;
