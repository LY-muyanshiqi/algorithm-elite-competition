clear; clc;
x=load('jie.txt');
%%
NH=load('hydro.txt');  %水电
NW=load('wind.txt');   %风电
NP=load('solar.txt');  %光伏
FH=load('FH.txt');    %陕西负荷
Zpump=1400; %抽蓄规模
h=4;        %抽蓄满发小时
%%  有抽蓄减碳计算
i=3; % 第几天
Nh=NH(i,:);
Nw=NW(i,:);
Np=NP(i,:);
L=FH(i,:);
V=Zpump*h;  %储能容量
N=Nh+Nw+Np;
C(1)=0.5; C(25)=0.5; %初始储能状态
for i=1:23
    C(i+1)=x(i);
end
for i=1:24
    if C(i+1)<=C(i) % 抽蓄发电
        Npump(i)=(C(i)-C(i+1))*V;
        if Npump(i)<Zpump*0.2
            Npump(i)=0;
            C(i+1)=C(i);
        end
        if Npump(i)>Zpump
            Npump(i)=Zpump;
            C(i+1)=C(i)-Npump(i)/V;
        end
    end
    if C(i+1)>C(i) % 抽蓄蓄水
        Npump(i)=(C(i)-C(i+1))*V/0.75;
        if Npump(i)>-Zpump*0.2
            Npump(i)=0;
            C(i+1)=C(i);
        end
        if Npump(i)<-Zpump
            Npump(i)=-Zpump;
            C(i+1)=C(i)-Npump(i)*0.75/V;
        end
    end
end

Nn=N+Npump; % 水风光抽蓄
Nt=L-Nn; %火电应承担负荷
Zt_f=(max(Nt)-min(Nt))/0.7; %火电参与调峰容量
if Zt_f>max(Nt)
    Nt_b=0; %火电基荷容量
else
    Nt_b=max(Nt)-Zt_f; %火电基荷容量
end
%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
OF=0.99; %修正的碳氧化率
Cc=0.7;  %含碳量
Mco2=44; %CO2摩尔量
Mc=12; %C摩尔量
e_100=0.953;e_50=0.934; e_40=0.92; e_30=0.904; %燃烧效率
g_100=0.458; g_50=0.442; g_40=0.424; g_30=0.401; %汽轮机绝对内效率
Cq=0.9183; %单位电量产生的CO2
a=0.02; %附加装置能耗占比
ps=0.01; %燃煤含硫量
us=0.95; %机组脱硫效率
Ms=32; %S摩尔量
as=0.0148; %脱硫能耗比
ys=0.00392; %脱硝能耗比
TH=Nt-Nt_b; %火电调峰运行过程
THmax=Zt_f; 
h=300; %供电煤耗
Emi_b=h*OF*Cc*Mco2/Mc*Nt_b; % 各时段火电承担基荷碳排放量
for i=1:24
    if TH(i)<THmax*0.3
        TH(i)=THmax*0.3;
    end
    if TH(i)<THmax*0.4
        H=370;%供电煤耗
        e(i)=e_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(e_40-e_30);
        g(i)=g_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(g_40-g_30);
        Ce1(i)=H*OF*Cc*Mco2/Mc;
        Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
        Ce3(i)=H*ps*us*Mco2/Ms+H*as*Cq+H*ys*Cq;
    else
        if TH(i)<THmax*0.5
            H=330;%供电煤耗
            e(i)=e_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(e_50-e_40);
            g(i)=g_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(g_50-g_40);
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
            Ce3(i)=0;
        else
            H=300;%供电煤耗
            e(i)=1;
            g(i)=1;
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=0;
            Ce3(i)=0;
        end
    end
    Ce(i)=Ce1(i)+Ce2(i)+Ce3(i); %火电调峰的各时段碳排放强度
    Emi(i)=Ce(i)*TH(i);
    EMI(i)=Emi(i)+Emi_b;
end
%%%%%%%%%%%%%火电调峰容量最小%%%%%%%%%%%
f(1)=Zt_f; 
%%%%%%%%%%%%%火电碳排放强度最小%%%%%%%%%%%
f(2)=sum(EMI)/sum(Nt); 
%%
figure
plot(L)
hold on
plot(N)
% hold on
% plot(Nn)

figure
plot(C)
