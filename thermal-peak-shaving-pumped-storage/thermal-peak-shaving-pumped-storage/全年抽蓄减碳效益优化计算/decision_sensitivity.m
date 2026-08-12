function sensitivity = decision_sensitivity(best_solution, V, Zpump, h, Nh, Nw, Np, L, Cprice)
% decision_sensitivity - 决策变量One-at-a-time敏感性分析
%
% 对最优解的每个决策变量施加 +/-10% 扰动, 观察目标函数变化

if nargin < 9, Cprice = 0.05; end

f0 = evaluate_objective(best_solution, 2, V, Nh, Nw, Np, L, Zpump, h, Cprice);

sensitivity = struct();
sensitivity.f0 = f0;
sensitivity.f1_sensitivity = zeros(V, 1);
sensitivity.f2_sensitivity = zeros(V, 1);
sensitivity.total_sensitivity = zeros(V, 1);

fprintf('=== 决策变量敏感性分析 ===\n');
fprintf('基准值: f1=%.1f, f2=%.1f\n\n', f0(1), f0(2));
fprintf('%-6s %-12s %-12s %-12s\n', 'Var', 'delta_f1', 'delta_f2', 'total');

for j = 1:V
    x_up = best_solution;
    x_down = best_solution;

    delta = 0.1 * abs(best_solution(j));
    if delta < 0.001, delta = 0.01; end

    x_up(j) = min(best_solution(j) + delta, 1);
    if j >= 22
        x_up(j) = min(best_solution(j) + delta, 1);
    end

    x_down(j) = max(best_solution(j) - delta, 0);
    if j == 22, x_down(22) = max(best_solution(22) - delta, 0.125); end
    if j == 23, x_down(23) = max(best_solution(23) - delta, 0.3125); end

    f_up = evaluate_objective(x_up, 2, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    f_down = evaluate_objective(x_down, 2, V, Nh, Nw, Np, L, Zpump, h, Cprice);

    delta_f1_up = abs(f_up(1) - f0(1)) / max(abs(f0(1)), 1);
    delta_f1_down = abs(f_down(1) - f0(1)) / max(abs(f0(1)), 1);
    delta_f2_up = abs(f_up(2) - f0(2)) / max(abs(f0(2)), 1);
    delta_f2_down = abs(f_down(2) - f0(2)) / max(abs(f0(2)), 1);

    sensitivity.f1_sensitivity(j) = (delta_f1_up + delta_f1_down) / 2;
    sensitivity.f2_sensitivity(j) = (delta_f2_up + delta_f2_down) / 2;
    sensitivity.total_sensitivity(j) = sensitivity.f1_sensitivity(j) + sensitivity.f2_sensitivity(j);

    if mod(j, 6) == 0 || j == V
        fprintf('%-6d %-12.4f %-12.4f %-12.4f\n', j, ...
            sensitivity.f1_sensitivity(j), sensitivity.f2_sensitivity(j), ...
            sensitivity.total_sensitivity(j));
    end
end

[~, rank_order] = sort(sensitivity.total_sensitivity, 'descend');
fprintf('\n--- 敏感度 Top10 决策变量 ---\n');
fprintf('Rank  Var    Total_Sens  主要影响目标\n');
for r = 1:min(10, V)
    j = rank_order(r);
    target = 'f1(调峰)';
    if sensitivity.f2_sensitivity(j) > sensitivity.f1_sensitivity(j)
        target = 'f2(碳排)';
    end
    fprintf('%-5d %-6d %-12.4f %s\n', r, j, sensitivity.total_sensitivity(j), target);
end

sensitivity.rank_order = rank_order;
sensitivity.top10 = rank_order(1:min(10, V));
end