function [f] = tanpafangjisuan(Zt_f, Nt_b, Nt)
% tanpafangjisuan - independent carbon emission calculation (continuous)
%
% Uses pchip to replace the three-segment step model
% Output: f(1)=Zt_f, f(2)=carbon intensity (gCO2/kWh), f(3)=total carbon

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
f(2) = sum(EMI) / sum(Nt);
f(3) = sum(EMI);
