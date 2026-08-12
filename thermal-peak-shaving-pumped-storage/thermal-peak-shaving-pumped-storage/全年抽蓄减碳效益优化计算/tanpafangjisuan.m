function [f]=tanpafangjisuan(Zt_f,Nt_b,Nt)
OF=0.99; %
Cc=0.7;  %
Mco2=44; %CO2
Mc=12; %C
e_100=0.953;e_50=0.934; e_40=0.92; e_30=0.904; %
g_100=0.458; g_50=0.442; g_40=0.424; g_30=0.401; %
Cq=0.9183; %CO2
a=0.02; %
ps=0.01; %
us=0.95; %
Ms=32; %S
as=0.0148; %
ys=0.00392; %
TH=Nt-Nt_b; %
THmax=Zt_f; 
h=300; %
Emi_b=h*OF*Cc*Mco2/Mc*Nt_b; % 
for i=1:24
    if TH(i)<THmax*0.3
        TH(i)=THmax*0.3;
    end
    if TH(i)<THmax*0.4
        H=370;%
        e(i)=e_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(e_40-e_30);
        g(i)=g_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(g_40-g_30);
        Ce1(i)=H*OF*Cc*Mco2/Mc;
        Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
        Ce3(i)=H*ps*us*Mco2/Ms+H*as*Cq+H*ys*Cq;
    else
        if TH(i)<THmax*0.5
            H=330;%
            e(i)=e_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(e_50-e_40);
            g(i)=g_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(g_50-g_40);
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
            Ce3(i)=0;
        else
            H=300;%
            e(i)=1;
            g(i)=1;
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=0;
            Ce3(i)=0;
        end
    end
    Ce(i)=Ce1(i)+Ce2(i)+Ce3(i); %
    Emi(i)=Ce(i)*TH(i);
    EMI(i)=Emi(i)+Emi_b;
end
%%%%%%%%%%%%%%%%%%%%%%%%
f(1)=Zt_f; 
%%%%%%%%%%%%%%%%%%%%%%%%
f(2)=sum(EMI)/sum(Nt);
f(3)=sum(EMI); %
 

