function m = compromise_solution(s, M, V)
if nargin < 2
    M = 2;
    V = 23;
end

obj_cols = (V+1):(V+M);
f1 = s(:, V+1);
f2 = s(:, V+2);

feasible = isfinite(f1) & isfinite(f2);
if ~any(feasible)
    % No valid candidate: return a deterministic first-row fallback rather
    % than allowing max/min on an empty set to create NaN scores.
    m = 1;
    return;
end

f1_max = max(f1(feasible)); f1_min = min(f1(feasible));
f2_max = max(f2(feasible)); f2_min = min(f2(feasible));

for i = 1:size(s, 1)
    if ~feasible(i)
        x(i, 1) = 0;
        x(i, 2) = 0;
    else
        f1_range = max(f1_max - f1_min, eps);
        f2_range = max(f2_max - f2_min, eps);
        x(i, 1) = (f1_max - f1(i)) / f1_range;
        x(i, 2) = (f2_max - f2(i)) / f2_range;
    end
end
X = sum(x, 2);
[~, m] = max(X);



