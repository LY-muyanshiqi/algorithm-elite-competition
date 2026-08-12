function [op_probs, q_table, epsilon] = q_learning_selector(state_features, q_table, epsilon, action, reward, gen, max_gen)
% q_learning_selector - Q-Learning 自适应算子选择器
%
% 状态空间 (6维, 每维离散化为3-5个桶):
%   1. 种群熵 (0-1)          -> 3 bins
%   2. 代数进度 (0-1)         -> 5 bins
%   3. 停滞计数 (log scale)   -> 3 bins
%   4. HV增量 (normalized)    -> 3 bins
%   5. 约束违反率 (0-1)       -> 3 bins
%   6. 拥挤距离方差 (0-1)     -> 3 bins
%
% 总状态数: 3*5*3*3*3*3 = 1215
%
% 动作空间 (7种算子):
%   1: DE/rand/1, 2: DE/rand/2, 3: DE/current-to-best/1
%   4: PM, 5: SBX, 6: Levy, 7: Cauchy
%
% 输入:
%   state_features - 6维特征向量 [entropy, gen_ratio, stagnation, hv_delta, cv_rate, crowd_var]
%   q_table        - Q表 (states x actions)
%   epsilon        - 当前探索率
%   action         - 上一步选择的动作 (1-7), 首次调用传0
%   reward         - 上一步的奖励, 首次调用传0
%   gen            - 当前代数
%   max_gen        - 最大代数
%
% 输出:
%   op_probs  - 7维算子选择概率向量
%   q_table   - 更新后的Q表
%   epsilon   - 更新后的探索率

persistent n_bins n_states prev_state prev_action alpha gamma

if isempty(n_bins)
    n_bins = [3, 5, 3, 3, 3, 3];
    n_states = prod(n_bins);
end
if isempty(alpha), alpha = 0.1; end
if isempty(gamma), gamma = 0.9; end

if isempty(q_table) || all(q_table(:) == 0)
    q_table = 0.01 * rand(n_states, 7);
    prev_state = 0;
    prev_action = 0;
end

if prev_state > 0 && prev_action > 0
    q_table(prev_state, prev_action) = q_table(prev_state, prev_action) + ...
        alpha * (reward + gamma * max(q_table(prev_state, :)) - q_table(prev_state, prev_action));
end

state_idx = discretize_state(state_features, n_bins);

epsilon = max(0.01, 0.3 * (1 - gen / max_gen));

if rand() < epsilon
    action_sel = randi(7);
else
    [~, action_sel] = max(q_table(state_idx, :));
end

prev_state = state_idx;
prev_action = action_sel;

op_probs = zeros(1, 7);
op_probs(action_sel) = 0.9;
op_probs = op_probs + 0.1 / 7;
op_probs = op_probs / sum(op_probs);
end

function idx = discretize_state(features, n_bins)
    idx = 0;
    stride = 1;

    feat = min(max(features(1), 0), 1 - 1e-10);
    bin = floor(feat * n_bins(1)) + 1;
    idx = idx + (bin - 1) * stride;
    stride = stride * n_bins(1);

    feat = min(max(features(2), 0), 1 - 1e-10);
    bin = floor(feat * n_bins(2)) + 1;
    idx = idx + (bin - 1) * stride;
    stride = stride * n_bins(2);

    feat = min(features(3), 3);
    bin = floor(feat) + 1;
    idx = idx + (bin - 1) * stride;
    stride = stride * n_bins(3);

    feat = min(max(features(4), -1), 1);
    bin = floor((feat + 1) * n_bins(4) / 2) + 1;
    bin = min(max(bin, 1), n_bins(4));
    idx = idx + (bin - 1) * stride;
    stride = stride * n_bins(4);

    feat = min(max(features(5), 0), 1 - 1e-10);
    bin = floor(feat * n_bins(5)) + 1;
    idx = idx + (bin - 1) * stride;
    stride = stride * n_bins(5);

    feat = min(max(features(6), 0), 1 - 1e-10);
    bin = floor(feat * n_bins(6)) + 1;
    idx = idx + (bin - 1) * stride;
end