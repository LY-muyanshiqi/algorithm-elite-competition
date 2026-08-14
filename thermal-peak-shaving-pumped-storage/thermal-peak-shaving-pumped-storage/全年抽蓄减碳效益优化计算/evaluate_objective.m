function f = evaluate_objective(x, M, VV, Nh, Nw, Np, L, Zpump, h, Cprice)
% evaluate_objective - objective evaluation (continuous carbon model)

f = [];
V = Zpump * h;
N = Nh + Nw + Np;

C(1) = 0.5;
C(25) = 0.5;
for i = 1:23
    C(i+1) = x(i);
end

for i = 1:24
    if C(i+1) <= C(i)
        Npump(i) = (C(i) - C(i+1)) * V;
        if Npump(i) < Zpump * 0.2
            Npump(i) = 0;
            C(i+1) = C(i);
        end
        if Npump(i) > Zpump
            Npump(i) = Zpump;
            C(i+1) = C(i) - Npump(i) / V;
        end
    end
    if C(i+1) > C(i)
        Npump(i) = (C(i) - C(i+1)) * V / 0.75;
        if Npump(i) > -Zpump * 0.2
            Npump(i) = 0;
            C(i+1) = C(i);
        end
        if Npump(i) < -Zpump
            Npump(i) = -Zpump;
            C(i+1) = C(i) - Npump(i) * 0.75 / V;
        end
    end
end

Nn = N + Npump;
Nt = L - Nn;
Zt_f = (max(Nt) - min(Nt)) / 0.7;

if Zt_f > max(Nt)
    Nt_b = 0;
else
    Nt_b = max(Nt) - Zt_f;
end

TH = Nt - Nt_b;
THmax = Zt_f;
for i = 1:24
    if TH(i) < THmax * 0.3
        TH(i) = THmax * 0.3;
    end
end

Emi_b = 300 * 0.99 * 0.7 * 44 / 12 * Nt_b;
load_ratio = TH ./ THmax;
[H_vec, e_vec, g_vec, Ce1_vec, Ce2_vec, Ce3_vec] = carbon_intensity_continuous(load_ratio);

for i = 1:24
    Ce(i) = Ce1_vec(i) + Ce2_vec(i) + Ce3_vec(i);
    Emi(i) = Ce(i) * TH(i);
    EMI(i) = Emi(i) + Emi_b;
end

f(1) = Zt_f;
f(2) = sum(EMI);

if abs(C(25) - 0.5) > 0.01
    f(1) = inf;
    f(2) = inf;
end

if length(f) ~= M
    error('The number of decision variables does not match your previous input.');
end
