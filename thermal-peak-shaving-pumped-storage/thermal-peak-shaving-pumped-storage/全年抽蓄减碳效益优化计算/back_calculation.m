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
f1=tanpafangjisuan(Zt_f,Nt_b,Nt); 

%% 无抽蓄减碳量计算
Nn2=N; % 水风光
Nt2=L-Nn2; %火电应承担负荷
Zt_f2=(max(Nt2)-min(Nt2))/0.7; %火电参与调峰容量
if Zt_f2>max(Nt2)
    Nt_b2=0; %火电基荷容量
else
    Nt_b2=max(Nt2)-Zt_f2; %火电基荷容量
end
f2=tanpafangjisuan(Zt_f2,Nt_b2,Nt2);
%%
A=[Npump',Nt',Nt2',L'];
figure
plot(L)
hold on
plot(N)
% hold on
% plot(Nn)

figure
plot(C)
