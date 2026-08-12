function f = initialize_variables_multi(N, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice, init_method)
% initialize_variables_multi - population initialization with multiple strategies
%
% Input:
%   N           - population size
%   M           - number of objectives
%   V           - number of decision variables
%   min_range   - lower bounds (1 x V)
%   max_range   - upper bounds (1 x V)
%   Nh,Nw,Np,L  - hydro/wind/solar/load data
%   Zpump,h,Cprice - pumped-storage params
%   init_method - 'logistic'|'tent'|'sobol'|'random' (default 'logistic')
%
% Output:
%   f - N x (M+V) population: V decision vars + M objective values

if nargin < 13
    init_method = 'logistic';
end

minv = min_range(:)';
maxv = max_range(:)';
K = M + V;

% Generate [0,1] covering sequence y (N x V)
switch lower(init_method)
    case 'tent'
        y = rand(1, V);
        for i = 1:N
            y(y < 0.5) = 2 * y(y < 0.5);
            y(y >= 0.5) = 2 * (1 - y(y >= 0.5));
            y_seq(i, :) = y;
        end
    case 'sobol'
        for d = 1:V
            y_seq(:, d) = sobol_seq(N, d);
        end
    case 'random'
        y_seq = rand(N, V);
    otherwise % 'logistic' default
        y = rand(1, V);
        for i = 1:N
            y = 4 * y .* (1 - y);
            y_seq(i, :) = y;
        end
end

% Map to decision variable range and evaluate objectives
for i = 1:N
    for j = 1:V
        f(i, j) = minv(j) + (maxv(j) - minv(j)) * y_seq(i, j);
    end
    f(i, V+1:K) = evaluate_objective(f(i, :), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
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