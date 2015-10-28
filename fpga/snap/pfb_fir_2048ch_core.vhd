-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity pfb_fir_2048ch_core_ip is
  port (
    pol0_in0 : in std_logic_vector( 8-1 downto 0 );
    pol1_in0 : in std_logic_vector( 8-1 downto 0 );
    sync : in std_logic_vector( 32-1 downto 0 );
    pol2_in0 : in std_logic_vector( 8-1 downto 0 );
    pol2_in1 : in std_logic_vector( 8-1 downto 0 );
    pol3_in0 : in std_logic_vector( 8-1 downto 0 );
    pol3_in1 : in std_logic_vector( 8-1 downto 0 );
    pol0_in1 : in std_logic_vector( 8-1 downto 0 );
    pol1_in1 : in std_logic_vector( 8-1 downto 0 );
    pol0_out0 : out std_logic_vector( 18-1 downto 0 );
    pol1_out0 : out std_logic_vector( 18-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 );
    pol2_out0 : out std_logic_vector( 18-1 downto 0 );
    pol3_out0 : out std_logic_vector( 18-1 downto 0 );
    pol0_out1 : out std_logic_vector( 18-1 downto 0 );
    pol1_out1 : out std_logic_vector( 18-1 downto 0 );
    pol2_out1 : out std_logic_vector( 18-1 downto 0 );
    pol3_out1 : out std_logic_vector( 18-1 downto 0 );
    clk : in std_logic
  );
end pfb_fir_2048ch_core_ip;

-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity pfb_fir_2048ch_core_ip_struct is
  port (
    pol0_in0 : in std_logic_vector( 8-1 downto 0 );
    pol1_in0 : in std_logic_vector( 8-1 downto 0 );
    sync : in std_logic_vector( 32-1 downto 0 );
    pol2_in0 : in std_logic_vector( 8-1 downto 0 );
    pol2_in1 : in std_logic_vector( 8-1 downto 0 );
    pol3_in0 : in std_logic_vector( 8-1 downto 0 );
    pol3_in1 : in std_logic_vector( 8-1 downto 0 );
    pol0_in1 : in std_logic_vector( 8-1 downto 0 );
    pol1_in1 : in std_logic_vector( 8-1 downto 0 );
    clk_1 : in std_logic;
    ce_1 : in std_logic;
    pol0_out0 : out std_logic_vector( 18-1 downto 0 );
    pol1_out0 : out std_logic_vector( 18-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 );
    pol2_out0 : out std_logic_vector( 18-1 downto 0 );
    pol3_out0 : out std_logic_vector( 18-1 downto 0 );
    pol0_out1 : out std_logic_vector( 18-1 downto 0 );
    pol1_out1 : out std_logic_vector( 18-1 downto 0 );
    pol2_out1 : out std_logic_vector( 18-1 downto 0 );
    pol3_out1 : out std_logic_vector( 18-1 downto 0 )
  );
end pfb_fir_2048ch_core_ip_struct;

architecture structural of pfb_fir_2048ch_core_ip_struct is
  component pfb_fir_2048ch_core_ip
    port ( 
      pol0_in0 : in std_logic_vector( 8-1 downto 0 );
      pol1_in0 : in std_logic_vector( 8-1 downto 0 );
      sync : in std_logic_vector( 32-1 downto 0 );
      pol2_in0 : in std_logic_vector( 8-1 downto 0 );
      pol2_in1 : in std_logic_vector( 8-1 downto 0 );
      pol3_in0 : in std_logic_vector( 8-1 downto 0 );
      pol3_in1 : in std_logic_vector( 8-1 downto 0 );
      pol0_in1 : in std_logic_vector( 8-1 downto 0 );
      pol1_in1 : in std_logic_vector( 8-1 downto 0 );
      pol0_out0 : out std_logic_vector( 18-1 downto 0 );
      pol1_out0 : out std_logic_vector( 18-1 downto 0 );
      sync_out : out std_logic_vector( 1-1 downto 0 );
      pol2_out0 : out std_logic_vector( 18-1 downto 0 );
      pol3_out0 : out std_logic_vector( 18-1 downto 0 );
      pol0_out1 : out std_logic_vector( 18-1 downto 0 );
      pol1_out1 : out std_logic_vector( 18-1 downto 0 );
      pol2_out1 : out std_logic_vector( 18-1 downto 0 );
      pol3_out1 : out std_logic_vector( 18-1 downto 0 );
      clk : in std_logic
    );
  end component;
begin
  pfb_fir_2048ch_core_ip_inst : pfb_fir_2048ch_core_ip  
  port map (
    pol0_in0 => pol0_in0,
    pol1_in0 => pol1_in0, 
    sync     => sync,      
    pol2_in0 => pol2_in0,  
    pol2_in1 => pol2_in1,  
    pol3_in0 => pol3_in0,  
    pol3_in1 => pol3_in1,  
    pol0_in1 => pol0_in1,  
    pol1_in1 => pol1_in1,  
    clk      => clk_1,       
    pol0_out0 => pol0_out0, 
    pol1_out0 => pol1_out0, 
    sync_out  => sync_out,  
    pol2_out0 => pol2_out0, 
    pol3_out0 => pol3_out0, 
    pol0_out1 => pol0_out1, 
    pol1_out1 => pol1_out1, 
    pol2_out1 => pol2_out1, 
    pol3_out1 => pol3_out1 
  );
end structural;
