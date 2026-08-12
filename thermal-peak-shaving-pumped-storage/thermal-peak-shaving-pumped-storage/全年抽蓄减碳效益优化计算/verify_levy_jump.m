function verify_levy_jump(n_samples, n_dims)
% verify_levy_jump - Levyvs
%
% Levy(Pareto)()

if nargin < 1, n_samples = 10000; end
if nargin < 2, n_dims = 10; end

fprintf('=== Levy ===\n');
fprintf(': %d, : %d\n\n', n_samples, n_dims);

beta = 1.5;
alpha = 0.01;
sigma_u = (gamma(1+beta)*sin(pi*beta/2) / (gamma((1+beta)/2)*beta*2^((beta-1)/2)))^(1/beta);

levy_steps = zeros(n_samples, n_dims);
gauss_steps = zeros(n_samples, n_dims);

for i = 1:n_samples
    u = normrnd(0, sigma_u, 1, n_dims);
    v = normrnd(0, 1, 1, n_dims);
    levy_steps(i, :) = u ./ (abs(v).^(1/beta));
    gauss_steps(i, :) = normrnd(0, 1, 1, n_dims);
end

levy_norms = sqrt(sum(levy_steps.^2, 2));
gauss_norms = sqrt(sum(gauss_steps.^2, 2));

fprintf('---  ---\n');
fprintf('  Levy:  mean=%.3f, std=%.3f, max=%.3f, skewness=%.3f\n', ...
    mean(levy_norms), std(levy_norms), max(levy_norms), skewness(levy_norms));
fprintf('  Gauss: mean=%.3f, std=%.3f, max=%.3f, skewness=%.3f\n', ...
    mean(gauss_norms), std(gauss_norms), max(gauss_norms), skewness(gauss_norms));

fprintf('\n---  (>3sigma) ---\n');
thresholds = [1, 2, 3, 5, 10, 20];
for t = thresholds
    p_levy = mean(levy_norms > t * mean(gauss_norms));
    p_gauss = mean(gauss_norms > t * mean(gauss_norms));
    ratio = p_levy / max(p_gauss, 1e-10);
    fprintf('  > %d sigma: Levy=%.6f, Gauss=%.6f, Ratio=%.0fx\n', t, p_levy, p_gauss, ratio);
end

fprintf('\n--- Rastrigin:  ---\n');
n_tests = 100;
escape_success_levy = zeros(n_tests, 1);
escape_success_gauss = zeros(n_tests, 1);
n_evals_levy = zeros(n_tests, 1);
n_evals_gauss = zeros(n_tests, 1);

for test = 1:n_tests
    x0 = rand(1, n_dims) * 10 - 5;
    [success, n_evals] = test_escape_levy(x0, alpha, beta, sigma_u, n_dims);
    escape_success_levy(test) = success;
    n_evals_levy(test) = n_evals;

    [success, n_evals] = test_escape_gauss(x0, 0.01, n_dims);
    escape_success_gauss(test) = success;
    n_evals_gauss(test) = n_evals;
end

fprintf('  Levy:  =%.2f%%, =%.1f\n', ...
    mean(escape_success_levy)*100, mean(n_evals_levy(n_evals_levy>0)));
fprintf('  Gauss: =%.2f%%, =%.1f\n', ...
    mean(escape_success_gauss)*100, mean(n_evals_gauss(n_evals_gauss>0)));

fprintf('\n:\n');
fprintf('  Levy(P(step>t)  t^(-beta) vs exp(-t^2))\n');
fprintf('  , Levy, .\n');
end

function [success, n_evals] = test_escape_levy(x0, alpha, beta, sigma_u, n_dims)
    f0 = rastrigin(x0);
    max_trials = 100;
    success = false;
    n_evals = 0;
    for t = 1:max_trials
        u = normrnd(0, sigma_u, 1, n_dims);
        v = normrnd(0, 1, 1, n_dims);
        step = u ./ (abs(v).^(1/beta));
        x_new = x0 + alpha * step;
        f_new = rastrigin(x_new);
        n_evals = n_evals + 1;
        if f_new < f0 - 1
            success = true;
            break;
        end
    end
end

function [success, n_evals] = test_escape_gauss(x0, alpha, n_dims)
    f0 = rastrigin(x0);
    max_trials = 100;
    success = false;
    n_evals = 0;
    for t = 1:max_trials
        step = normrnd(0, alpha, 1, n_dims);
        x_new = x0 + step;
        f_new = rastrigin(x_new);
        n_evals = n_evals + 1;
        if f_new < f0 - 1
            success = true;
            break;
        end
    end
end

function f = rastrigin(x)
    A = 10;
    f = A * length(x) + sum(x.^2 - A * cos(2*pi*x));
end