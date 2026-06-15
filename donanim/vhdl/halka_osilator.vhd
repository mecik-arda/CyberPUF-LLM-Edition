library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity halka_osilator is
    generic (
        INVERTER_SAYISI : integer := 3;
        CHAIN_ID      : integer := 0
    );
    port (
        enable      : in  std_logic;
        osc_out     : out std_logic
    );
end entity halka_osilator;

architecture rtl of halka_osilator is

    signal chain : std_logic_vector(INVERTER_SAYISI - 1 downto 0);

    attribute DONT_TOUCH : string;
    attribute DONT_TOUCH of chain : signal is "TRUE";

    attribute KEEP : string;
    attribute KEEP of chain : signal is "TRUE";

    attribute ALLOW_COMBINATORIAL_LOOPS : string;
    attribute ALLOW_COMBINATORIAL_LOOPS of chain : signal is "TRUE";

begin

    assert (INVERTER_SAYISI mod 2 = 1) report "INVERTER_SAYISI tek sayi olmalidir!" severity failure;

    chain(0) <= not chain(INVERTER_SAYISI - 1) after 1 ns when enable = '1' else '0';

    gen_inverters: for i in 1 to INVERTER_SAYISI - 1 generate
        chain(i) <= not chain(i - 1) after 1 ns when enable = '1' else '0';
    end generate gen_inverters;

    osc_out <= chain(INVERTER_SAYISI - 1);

end architecture rtl;
