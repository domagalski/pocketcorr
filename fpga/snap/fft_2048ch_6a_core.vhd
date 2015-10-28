-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity fft_2048ch_6a_core_ip is
  port (
    pol0_in0 : in std_logic_vector( 18-1 downto 0 );
    pol0_in1 : in std_logic_vector( 18-1 downto 0 );
    pol1_in0 : in std_logic_vector( 18-1 downto 0 );
    pol1_in1 : in std_logic_vector( 18-1 downto 0 );
    pol2_in0 : in std_logic_vector( 18-1 downto 0 );
    pol2_in1 : in std_logic_vector( 18-1 downto 0 );
    pol3_in0 : in std_logic_vector( 18-1 downto 0 );
    pol3_in1 : in std_logic_vector( 18-1 downto 0 );
    pol4_in0 : in std_logic_vector( 18-1 downto 0 );
    pol4_in1 : in std_logic_vector( 18-1 downto 0 );
    pol5_in0 : in std_logic_vector( 18-1 downto 0 );
    pol5_in1 : in std_logic_vector( 18-1 downto 0 );
    shift : in std_logic_vector( 16-1 downto 0 );
    sync : in std_logic_vector( 32-1 downto 0 );
    clk : in std_logic;
    out0 : out std_logic_vector( 36-1 downto 0 );
    out1 : out std_logic_vector( 36-1 downto 0 );
    out2 : out std_logic_vector( 36-1 downto 0 );
    out3 : out std_logic_vector( 36-1 downto 0 );
    out4 : out std_logic_vector( 36-1 downto 0 );
    out5 : out std_logic_vector( 36-1 downto 0 );
    overflow : out std_logic_vector( 6-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 )
  );
end fft_2048ch_6a_core_ip;

-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity fft_2048ch_6a_core_ip_struct is
  port (
    pol0_in0 : in std_logic_vector( 18-1 downto 0 );
    pol0_in1 : in std_logic_vector( 18-1 downto 0 );
    pol1_in0 : in std_logic_vector( 18-1 downto 0 );
    pol1_in1 : in std_logic_vector( 18-1 downto 0 );
    pol2_in0 : in std_logic_vector( 18-1 downto 0 );
    pol2_in1 : in std_logic_vector( 18-1 downto 0 );
    pol3_in0 : in std_logic_vector( 18-1 downto 0 );
    pol3_in1 : in std_logic_vector( 18-1 downto 0 );
    pol4_in0 : in std_logic_vector( 18-1 downto 0 );
    pol4_in1 : in std_logic_vector( 18-1 downto 0 );
    pol5_in0 : in std_logic_vector( 18-1 downto 0 );
    pol5_in1 : in std_logic_vector( 18-1 downto 0 );
    shift : in std_logic_vector( 16-1 downto 0 );
    sync : in std_logic_vector( 32-1 downto 0 );
    clk_1 : in std_logic;
    ce_1 : in std_logic;
    out0 : out std_logic_vector( 36-1 downto 0 );
    out1 : out std_logic_vector( 36-1 downto 0 );
    out2 : out std_logic_vector( 36-1 downto 0 );
    out3 : out std_logic_vector( 36-1 downto 0 );
    out4 : out std_logic_vector( 36-1 downto 0 );
    out5 : out std_logic_vector( 36-1 downto 0 );
    overflow : out std_logic_vector( 6-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 )
  );
end fft_2048ch_6a_core_ip_struct;

architecture structural of fft_2048ch_6a_core_ip_struct is
  component fft_2048ch_6a_core_ip
    port (
      pol0_in0 : in std_logic_vector( 18-1 downto 0 );
      pol0_in1 : in std_logic_vector( 18-1 downto 0 );
      pol1_in0 : in std_logic_vector( 18-1 downto 0 );
      pol1_in1 : in std_logic_vector( 18-1 downto 0 );
      pol2_in0 : in std_logic_vector( 18-1 downto 0 );
      pol2_in1 : in std_logic_vector( 18-1 downto 0 );
      pol3_in0 : in std_logic_vector( 18-1 downto 0 );
      pol3_in1 : in std_logic_vector( 18-1 downto 0 );
      pol4_in0 : in std_logic_vector( 18-1 downto 0 );
      pol4_in1 : in std_logic_vector( 18-1 downto 0 );
      pol5_in0 : in std_logic_vector( 18-1 downto 0 );
      pol5_in1 : in std_logic_vector( 18-1 downto 0 );
      shift : in std_logic_vector( 16-1 downto 0 );
      sync : in std_logic_vector( 32-1 downto 0 );
      clk : in std_logic;
      out0 : out std_logic_vector( 36-1 downto 0 );
      out1 : out std_logic_vector( 36-1 downto 0 );
      out2 : out std_logic_vector( 36-1 downto 0 );
      out3 : out std_logic_vector( 36-1 downto 0 );
      out4 : out std_logic_vector( 36-1 downto 0 );
      out5 : out std_logic_vector( 36-1 downto 0 );
      overflow : out std_logic_vector( 6-1 downto 0 );
      sync_out : out std_logic_vector( 1-1 downto 0 )
    );
  end component;
begin
  fft_2048ch_6a_core_ip_inst : fft_2048ch_6a_core_ip
  port map (
    pol0_in0 => pol0_in0, 
    pol0_in1 => pol0_in1, 
    pol1_in0 => pol1_in0, 
    pol1_in1 => pol1_in1, 
    pol2_in0 => pol2_in0, 
    pol2_in1 => pol2_in1, 
    pol3_in0 => pol3_in0, 
    pol3_in1 => pol3_in1, 
    pol4_in0 => pol4_in0, 
    pol4_in1 => pol4_in1, 
    pol5_in0 => pol5_in0, 
    pol5_in1 => pol5_in1, 
    shift    => shift   , 
    sync     => sync    , 
    clk      => clk_1   , 
    out0     => out0    , 
    out1     => out1    , 
    out2     => out2    , 
    out3     => out3    , 
    out4     => out4    , 
    out5     => out5    , 
    overflow => overflow, 
    sync_out => sync_out 
  );
end structural; 
