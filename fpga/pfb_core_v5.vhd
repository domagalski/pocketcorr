library IEEE;
use IEEE.std_logic_1164.all;

entity pfb_core_v5 is
  port (
    ce_1: in std_logic; 
    clk_1: in std_logic; 
    pol1_in1: in std_logic_vector(15 downto 0); 
    sync: in std_logic; 
    pol1_out1: out std_logic_vector(35 downto 0); 
    sync_out: out std_logic
  );
end pfb_core_v5;

architecture structural of pfb_core_v5 is
begin
end structural;

