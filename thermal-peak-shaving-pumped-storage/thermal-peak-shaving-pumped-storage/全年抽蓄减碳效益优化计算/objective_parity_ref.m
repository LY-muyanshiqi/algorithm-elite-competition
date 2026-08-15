% objective_parity_ref.m - 生成 numpy 复刻对拍的 MATLAB 参考值
% 用法: matlab -batch "objective_parity_ref"
% 读取 parity_input.mat (随机解集)，输出 parity_ref.mat (参考 f1/f2)

clear;

if ~exist('parity_input.mat', 'file')
    error('parity_input.mat not found');
end

S = load('parity_input.mat');
X = S.X;           % N x 23 决策变量
Nh = S.Nh;         % 1 x 24
Nw = S.Nw;
Np = S.Np;
L = S.L;
Zpump = S.Zpump;
h = S.h;

N = size(X, 1);
F = zeros(N, 2);
M = 2;
VV = 23;

for i = 1:N
    f = evaluate_objective(X(i, :), M, VV, Nh, Nw, Np, L, Zpump, h, 0);
    F(i, 1) = f(1);
    F(i, 2) = f(2);
end

save('parity_ref.mat', 'F');
fprintf('parity_ref.mat written, N=%d\n', N);
