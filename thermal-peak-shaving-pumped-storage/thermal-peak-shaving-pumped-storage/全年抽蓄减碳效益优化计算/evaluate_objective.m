function f = evaluate_objective(x, M, VV,Nh,Nw,Np,L,Zpump,h,Cprice)
% clear;clc;
% M=2;
% x=rand(1,23);
f = [];
V=Zpump*h;  %��������
N=Nh+Nw+Np;
C(1)=0.5; C(25)=0.5; %��ʼ����״̬
for i=1:23
    C(i+1)=x(i);
end
for i=1:24
    if C(i+1)<=C(i) % �����
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
    if C(i+1)>C(i) % ������ˮ
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

Nn=N+Npump; % ˮ������
Nt=L-Nn; %���Ӧ�е�����
Zt_f=(max(Nt)-min(Nt))/0.7; %�������������
if Zt_f>max(Nt)
    Nt_b=0; %����������
else
    Nt_b=max(Nt)-Zt_f; %����������
end
%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
OF=0.99; %������̼������
Cc=0.7;  %��̼��
Mco2=44; %CO2Ħ����
Mc=12; %CĦ����
e_100=0.953;e_50=0.934; e_40=0.92; e_30=0.904; %ȼ��Ч��
g_100=0.458; g_50=0.442; g_40=0.424; g_30=0.401; %���ֻ�������Ч��
Cq=0.9183; %��λ����������CO2
a=0.02; %����װ���ܺ�ռ��
ps=0.01; %ȼú������
us=0.95; %��������Ч��
Ms=32; %SĦ����
as=0.0148; %�����ܺı�
ys=0.00392; %�����ܺı�
TH=Nt-Nt_b; %���������й���
THmax=Zt_f; 
h=300; %����ú��
Emi_b=h*OF*Cc*Mco2/Mc*Nt_b; % ��ʱ�λ��е�����̼�ŷ���
for i=1:24
    if TH(i)<THmax*0.3
        TH(i)=THmax*0.3;
    end
    if TH(i)<THmax*0.4
        H=370;%����ú��
        e(i)=e_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(e_40-e_30);
        g(i)=g_30+((TH(i)-THmax*0.3)/(THmax*0.4-THmax*0.3))*(g_40-g_30);
        Ce1(i)=H*OF*Cc*Mco2/Mc;
        Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
        Ce3(i)=H*ps*us*Mco2/Ms+H*as*Cq+H*ys*Cq;
    else
        if TH(i)<THmax*0.5
            H=330;%����ú��
            e(i)=e_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(e_50-e_40);
            g(i)=g_40+((TH(i)-THmax*0.4)/(THmax*0.5-THmax*0.4))*(g_50-g_40);
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=H*(1-e(i)/e_100)*Cq+H*(1-g(i)/g_100)*Cq+a*H*Cq;
            Ce3(i)=0;
        else
            H=300;%����ú��
            e(i)=1;
            g(i)=1;
            Ce1(i)=H*OF*Cc*Mco2/Mc;
            Ce2(i)=0;
            Ce3(i)=0;
        end
    end
    Ce(i)=Ce1(i)+Ce2(i)+Ce3(i); %������ĸ�ʱ��̼�ŷ�ǿ��
    Emi(i)=Ce(i)*TH(i);
    EMI(i)=Emi(i)+Emi_b;
end
%%%%%%%%%%%%%������������С%%%%%%%%%%%
f(1)=Zt_f; 
%%%%%%%%%%%%%���̼�ŷ�liang��С%%%%%%%%%%%
f(2)=sum(EMI); 

if abs(C(25)-0.5)>0
    f(1)=999999999999; 
    f(2)=999999999999;
end

%% Check for error
if length(f) ~= M
    error('The number of decision variables does not match you previous input. Kindly check your objective function');
end