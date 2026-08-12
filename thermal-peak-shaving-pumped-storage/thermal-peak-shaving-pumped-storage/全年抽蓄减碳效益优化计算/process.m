function [f1,f2,Npump,Nt,Nt2,L]=process(x,d)
%%
NH=load('hydro.txt');  %
NW=load('wind.txt');   %
NP=load('solar.txt');  %
FH=load('FH.txt');    %
Zpump=1400; %
h=4;        %
%%  
Nh=NH(d,:);
Nw=NW(d,:);
Np=NP(d,:);
L=FH(d,:);
V=Zpump*h;  %
N=Nh+Nw+Np;
C(1)=0.5; C(25)=0.5; %
for i=1:23
    C(i+1)=x(i);
end
for i=1:24
    if C(i+1)<=C(i) % 
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
    if C(i+1)>C(i) % 
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

Nn=N+Npump; % 
Nt=L-Nn; %
Zt_f=(max(Nt)-min(Nt))/0.7; %
if Zt_f>max(Nt)
    Nt_b=0; %
else
    Nt_b=max(Nt)-Zt_f; %
end
f1=tanpafangjisuan(Zt_f,Nt_b,Nt); 

%% 
Nn2=N; % 
Nt2=L-Nn2; %
Zt_f2=(max(Nt2)-min(Nt2))/0.7; %
if Zt_f2>max(Nt2)
    Nt_b2=0; %
else
    Nt_b2=max(Nt2)-Zt_f2; %
end
f2=tanpafangjisuan(Zt_f2,Nt_b2,Nt2);
%%
% figure
% plot(L)
% hold on
% plot(N)
% % hold on
% % plot(Nn)
% 
% figure
% plot(C)
