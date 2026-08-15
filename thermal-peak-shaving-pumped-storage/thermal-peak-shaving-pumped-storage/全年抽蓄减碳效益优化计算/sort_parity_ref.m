% sort_parity_ref.m - 非支配排序对拍的 MATLAB 参考值生成
% 用法: matlab -batch "sort_parity_ref"
% 读取 sort_input.mat (随机种群 X: N x (V+M))，输出 sort_ref.mat (排序后种群)

clear;

if ~exist('sort_input.mat', 'file')
    error('sort_input.mat not found');
end

S = load('sort_input.mat');
X = S.X;  % N x 25 (决策23 + 目标2)
M = S.M;
V = S.V;

% 调用 non_domination_sort_mod 得到排序后种群（含 rank + crowding）
sorted = non_domination_sort_mod(X, M, V);

save('sort_ref.mat', 'sorted');
fprintf('sort_ref.mat written, size %dx%d\n', size(sorted, 1), size(sorted, 2));
