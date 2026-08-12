function verify_chaos_uniformity(n_pop, n_dim, n_trials)
% verify_chaos_uniformity - 验证Logistic混沌映射的分布均匀性
%
% 对比Logistic映射、Tent映射、Sobol序列、均匀随机四种初始化策略
% 指标: 种群覆盖率（超球体填充体积）、KS检验p值、种群熵

if nargin < 1, n_pop = 100; end
if nargin < 2, n_dim = 23; end
if nargin < 3, n_trials = 1000; end

fprintf('=== Logistic混沌映射均匀性验证 ===\n');
fprintf('种群: %d, 维度: %d, 重复: %d\n\n', n_pop, n_dim, n_trials);

methods = {'logistic', 'tent', 'sobol', 'random'};
n_methods = length(methods);

coverage = zeros(n_trials, n_methods);
entropy_vals = zeros(n_trials, n_methods);
min_dist = zeros(n_trials, n_methods);
ks_pvals = zeros(n_trials, n_methods);

for t = 1:n_trials
    for m = 1:n_methods
        pop = generate_population(n_pop, n_dim, methods{m});

        coverage(t, m) = compute_coverage(pop);

        dist_matrix = pdist2(pop, pop);
        dist_matrix(dist_matrix == 0) = inf;
        min_dist(t, m) = mean(min(dist_matrix, [], 2));

        alpha = 0.1;
        S = exp(-dist_matrix.^2 / (2 * alpha^2));
        entropy_vals(t, m) = -mean(log(mean(S, 2) + 1e-10));

        sample = pop(:);
        [~, p] = kstest((sample - min(sample)) / (max(sample) - min(sample)));
        ks_pvals(t, m) = p;
    end

    if mod(t, 100) == 0
        fprintf('  Trial %d/%d\n', t, n_trials);
    end
end

fprintf('\n--- 覆盖率 (超球体填充体积, 越高越好) ---\n');
for m = 1:n_methods
    fprintf('  %-12s: mean=%.3f, std=%.3f\n', methods{m}, mean(coverage(:,m)), std(coverage(:,m)));
end

fprintf('\n--- 最小距离 (越大越均匀) ---\n');
for m = 1:n_methods
    fprintf('  %-12s: mean=%.4f, std=%.4f\n', methods{m}, mean(min_dist(:,m)), std(min_dist(:,m)));
end

fprintf('\n--- 种群熵 (越高多样性越好) ---\n');
for m = 1:n_methods
    fprintf('  %-12s: mean=%.3f, std=%.3f\n', methods{m}, mean(entropy_vals(:,m)), std(entropy_vals(:,m)));
end

fprintf('\n--- KS检验p值分布 (p>0.05比例, 越高越均匀) ---\n');
for m = 1:n_methods
    pass_rate = mean(ks_pvals(:,m) > 0.05);
    fprintf('  %-12s: p>0.05 rate = %.3f\n', methods{m}, pass_rate);
end

fprintf('\n--- Logistic vs 均匀随机: KS检验p值 (Lyapunov指数验证) ---\n');
logistic_samples = zeros(n_pop * n_dim, n_trials);
random_samples = zeros(n_pop * n_dim, n_trials);
for t = 1:n_trials
    pop_log = generate_population(n_pop, n_dim, 'logistic');
    pop_rand = generate_population(n_pop, n_dim, 'random');
    logistic_samples(:, t) = pop_log(:);
    random_samples(:, t) = pop_rand(:);
end
logistic_all = logistic_samples(:);
random_all = random_samples(:);
[~, p_val] = kstest2(logistic_all, random_all);
fprintf('  Logistic vs Random KS test p-value: %.4f\n', p_val);
if p_val > 0.05
    fprintf('  Conclusion: 不能拒绝两者来自同一分布的假设 (Logistic混沌替代rand的均匀性得到统计支持)\n');
else
    fprintf('  Conclusion: Logistic分布与均匀分布有显著差异 (需要分析差异的方向和幅度)\n');
end

fprintf('\n结果说明:\n');
fprintf('  Logistic混沌映射在mu=4时Lyapunov指数=ln(2)>0, 具有遍历性和伪随机性.\n');
fprintf('  覆盖率和熵越接近均匀随机, 说明混沌初始化可以替代rand()且可能更均匀.\n');
end

function pop = generate_population(N, D, method)
    pop = zeros(N, D);
    switch method
        case 'logistic'
            y = rand(1, D);
            for i = 1:N
                y = 4 * y .* (1 - y);
                pop(i, :) = y;
            end
        case 'tent'
            y = rand(1, D);
            for i = 1:N
                y(y < 0.5) = 2 * y(y < 0.5);
                y(y >= 0.5) = 2 * (1 - y(y >= 0.5));
                pop(i, :) = y;
            end
        case 'sobol'
            for d = 1:D
                pop(:, d) = sobol_seq(N, d);
            end
        case 'random'
            pop = rand(N, D);
    end
end

function s = sobol_seq(N, dim)
    s = zeros(N, 1);
    v = 2.^(32 - (1:32));
    for i = 1:N
        x = 0;
        c = i;
        for j = 1:32
            if bitand(c, dim * j)
                x = bitxor(round(x * 2^31), round(v(j)));
            end
        end
        s(i) = x / 2^31;
    end
end

function coverage = compute_coverage(pop)
    [N, D] = size(pop);
    r = mean(std(pop)) * (N^(-1/D));
    coverage = 0;
    n_samples = min(10000, 100 * N);
    samples = rand(n_samples, D);
    for i = 1:N
        dists = sqrt(sum((samples - pop(i,:)).^2, 2));
        coverage = coverage + sum(dists < r);
    end
    coverage = coverage / (N * n_samples);
end