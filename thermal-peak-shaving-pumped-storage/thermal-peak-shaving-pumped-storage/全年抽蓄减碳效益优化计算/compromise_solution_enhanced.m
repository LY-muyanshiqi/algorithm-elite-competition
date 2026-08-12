function [best_solution, best_idx, decision_report] = compromise_solution_enhanced(chromosome, M, V, Zpump, h, carbon_price)
% compromise_solution_enhanced - TOPSIS + VIKOR + GRA 
%
% :
%   Layer1: 
%   Layer2: 
%   Layer3: TOPSIS + VIKOR + GRA  + 
%
%  compromise_solution.m:
%   1.  TOPSIS  ( + )
%   2. : Layer1 -> Layer2 -> Layer3 MADM
%   3.  ( M,V )
%
% :
%   chromosome   -  (N x (V+M+2))
%   M, V         - 
%   Zpump        -  (MW)
%   h            - 
%   carbon_price -  (/tCO2), , 100
%
% :
%   best_solution   -  (1xV)
%   best_idx        - 
%   decision_report - 

if nargin < 6
    carbon_price = 100;
end

[N, K] = size(chromosome);
obj_cols = (V+1):(V+M);

%% ===== Layer 1: Engineering Feasibility Filter =====
feasible = true(N, 1);
for i = 1:N
    x = chromosome(i, 1:V);
    C_states = [0.5, x, 0.5];
    C_range = max(C_states) - min(C_states);

    f1 = chromosome(i, V+1);
    f2 = chromosome(i, V+2);

    if isinf(f1) || isinf(f2)
        feasible(i) = false;
    end
    if C_range > 0.95
        feasible(i) = false;
    end
end

feasible_idx = find(feasible);
if isempty(feasible_idx)
    feasible_idx = (1:N)';
end
P1 = chromosome(feasible_idx, :);
n1 = length(feasible_idx);

%% ===== Layer 2: Economic Evaluation =====
economic_scores = zeros(n1, 1);
for i = 1:n1
    carbon_reduction = 5000 - P1(i, V+2);
    if carbon_reduction < 0, carbon_reduction = 0; end
    carbon_revenue = carbon_reduction * carbon_price / 10000;
    pump_revenue = Zpump * h * 0.3 * 365 / 10000;
    economic_scores(i) = carbon_revenue + pump_revenue;
end

%% ===== Layer 3: MADM with Standard TOPSIS =====
obj_data = P1(:, obj_cols);
f1_data = obj_data(:, 1);
f2_data = obj_data(:, 2);

eco_data = economic_scores;
obj_all = [f1_data, f2_data, eco_data];
obj_all(:, 4) = 1 - abs(P1(:, end) - 0.01);

direction = [-1, -1, 1, -1];

[n_obj, m_obj] = size(obj_all);
norm_data = zeros(n_obj, m_obj);
for j = 1:m_obj
    col = obj_all(:, j);
    rms_val = sqrt(sum(col.^2));
    if rms_val > 0
        norm_data(:, j) = col / rms_val;
    else
        norm_data(:, j) = col;
    end
end

W = entropy_weight(norm_data);

ideal_best = zeros(1, m_obj);
ideal_worst = zeros(1, m_obj);
for j = 1:m_obj
    if direction(j) == 1
        ideal_best(j) = max(norm_data(:, j));
        ideal_worst(j) = min(norm_data(:, j));
    else
        ideal_best(j) = min(norm_data(:, j));
        ideal_worst(j) = max(norm_data(:, j));
    end
end

S_best = zeros(n_obj, 1);
S_worst = zeros(n_obj, 1);
for i = 1:n_obj
    S_best(i) = sqrt(sum(W .* (norm_data(i, :) - ideal_best).^2));
    S_worst(i) = sqrt(sum(W .* (norm_data(i, :) - ideal_worst).^2));
end

C_scores = S_worst ./ (S_best + S_worst);
[top_closeness, top_order] = sort(C_scores, 'descend');

best_idx = feasible_idx(top_order(1));
best_solution = chromosome(best_idx, 1:V);

% TOPSIS rankings
top5_topsis = feasible_idx(top_order(1:min(5, length(top_order))));

%% ===== VIKOR Method =====
v = 0.5;
S_vikor = zeros(n_obj, 1);
R_vikor = zeros(n_obj, 1);

for j = 1:m_obj
    w_j = W(j);
    if direction(j) == 1
        f_best = max(norm_data(:, j));
        f_worst = min(norm_data(:, j));
    else
        f_best = min(norm_data(:, j));
        f_worst = max(norm_data(:, j));
    end
    range_j = f_worst - f_best;
    if range_j > 0
        for i = 1:n_obj
            d = w_j * abs(f_best - norm_data(i, j)) / range_j;
            S_vikor(i) = S_vikor(i) + d;
            R_vikor(i) = max(R_vikor(i), d);
        end
    end
end

S_star = min(S_vikor); S_minus = max(S_vikor);
R_star = min(R_vikor); R_minus = max(R_vikor);
Q_vikor = zeros(n_obj, 1);
for i = 1:n_obj
    if S_minus > S_star
        Q_vikor(i) = v * (S_vikor(i) - S_star) / (S_minus - S_star) + ...
                     (1 - v) * (R_vikor(i) - R_star) / (R_minus - R_star);
    end
end

[~, vikor_order] = sort(Q_vikor);
top5_vikor = feasible_idx(vikor_order(1:min(5, length(vikor_order))));

%% ===== GRA Method (Grey Relational Analysis) =====
rho = 0.5;
ref_seq = zeros(1, m_obj);
for j = 1:m_obj
    if direction(j) == 1
        ref_seq(j) = max(norm_data(:, j));
    else
        ref_seq(j) = min(norm_data(:, j));
    end
end

grc = zeros(n_obj, m_obj);
for j = 1:m_obj
    abs_diff = abs(ref_seq(j) - norm_data(:, j));
    min_diff = min(abs_diff);
    max_diff = max(abs_diff);
    if max_diff > min_diff
        grc(:, j) = (min_diff + rho * max_diff) ./ (abs_diff + rho * max_diff);
    else
        grc(:, j) = 1;
    end
end

G_scores = grc * W(:);

[~, gra_order] = sort(G_scores, 'descend');
top5_gra = feasible_idx(gra_order(1:min(5, length(gra_order))));

%% ===== Kendall's Tau  =====
tau_topsis_vikor = kendall_tau(top_order, vikor_order);
tau_topsis_gra = kendall_tau(top_order, gra_order);
tau_vikor_gra = kendall_tau(vikor_order, gra_order);

%% ===== Decision Report =====
decision_report = struct();
decision_report.layer1_n_total = N;
decision_report.layer1_n_after_filter = n1;
decision_report.layer1_filter_rate = n1 / N * 100;
decision_report.layer2_economic_scores = economic_scores;
decision_report.layer2_best_economic = max(economic_scores);
decision_report.layer3_method = 'TOPSIS + VIKOR + GRA (Entropy Weight)';
decision_report.layer3_weights = W;
decision_report.layer3_closeness = C_scores;
decision_report.layer3_best_closeness = max(C_scores);
decision_report.layer3_top5_topsis = top5_topsis;
decision_report.layer3_top5_vikor = top5_vikor;
decision_report.layer3_top5_gra = top5_gra;
decision_report.layer3_tau_topsis_vikor = tau_topsis_vikor;
decision_report.layer3_tau_topsis_gra = tau_topsis_gra;
decision_report.layer3_tau_vikor_gra = tau_vikor_gra;
decision_report.final_best_idx = best_idx;
decision_report.final_f1 = chromosome(best_idx, V+1);
decision_report.final_f2 = chromosome(best_idx, V+2);

fprintf('\n===  ===\n');
fprintf('TOPSIS    Top3: %s\n', mat2str(top5_topsis(1:min(3,end))'));
fprintf('VIKOR     Top3: %s\n', mat2str(top5_vikor(1:min(3,end))'));
fprintf('GRA       Top3: %s\n', mat2str(top5_gra(1:min(3,end))'));
fprintf('Kendall tau: T-V=%.3f, T-G=%.3f, V-G=%.3f\n', tau_topsis_vikor, tau_topsis_gra, tau_vikor_gra);

end

function tau = kendall_tau(rank_a, rank_b)
    n = min(length(rank_a), length(rank_b));
    concordant = 0;
    discordant = 0;
    for i = 1:n
        for j = i+1:n
            if (rank_a(i) < rank_a(j) && rank_b(i) < rank_b(j)) || ...
               (rank_a(i) > rank_a(j) && rank_b(i) > rank_b(j))
                concordant = concordant + 1;
            else
                discordant = discordant + 1;
            end
        end
    end
    tau = (concordant - discordant) / (n * (n - 1) / 2);
end

function W = entropy_weight(norm_data)
    [n, m] = size(norm_data);
    shifted = norm_data - min(norm_data) + 1e-10;
    P = shifted ./ sum(shifted);
    E = -sum(P .* log(P + 1e-10)) / log(n);
    D = 1 - E;
    W = D / sum(D);
end
