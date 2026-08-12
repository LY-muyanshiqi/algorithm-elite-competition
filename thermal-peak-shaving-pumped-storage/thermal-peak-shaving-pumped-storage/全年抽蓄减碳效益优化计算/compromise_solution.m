function m = compromise_solution(s, M, V)
if nargin < 2
    M = 2;
    V = 23;
end

obj_cols = (V+1):(V+M);
f1 = s(:, V+1);
f2 = s(:, V+2);

f1_max = max(f1); f1_min = min(f1);
f2_max = max(f2); f2_min = min(f2);

for i = 1:size(s, 1)
    if isinf(f1(i)) || isinf(f2(i))
        x(i, 1) = 0;
        x(i, 2) = 0;
    else
        x(i, 1) = (f1_max - f1(i)) / (f1_max - f1_min);
        x(i, 2) = (f2_max - f2(i)) / (f2_max - f2_min);
    end
end
X = sum(x, 2);
[~, m] = max(X);



