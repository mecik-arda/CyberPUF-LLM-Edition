library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity aes256_anahtar_genisletme is
    port (
        clk             : in  std_logic;
        rst             : in  std_logic;
        anahtar_giris          : in  std_logic_vector(255 downto 0);
        start           : in  std_logic;
        tur_anahtarlari      : out tur_anahtar_dizisi_t;
        done            : out std_logic;
        busy            : out std_logic
    );
end entity aes256_anahtar_genisletme;

architecture rtl of aes256_anahtar_genisletme is

    type state_t is (IDLE, LOAD_KEY, EXPAND, FINISHED, DONE_PULSE);
    signal state : state_t;

    signal w : kelime_dizisi_t(0 to 59);
    signal tur_indeksi : unsigned(5 downto 0);

begin

    process(clk, rst)
        variable gecici_kelime : std_logic_vector(31 downto 0);
        variable rcon_val  : std_logic_vector(31 downto 0);
        variable idx       : integer;
    begin
        if rst = '1' then
            state <= IDLE;
            done <= '0';
            busy <= '0';
            tur_indeksi <= (others => '0');
            for i in 0 to 59 loop
                w(i) <= (others => '0');
            end loop;
            for i in 0 to 14 loop
                tur_anahtarlari(i) <= (others => '0');
            end loop;
        elsif rising_edge(clk) then
            done <= '0';

            case state is
                when IDLE =>
                    busy <= '0';
                    if start = '1' then
                        state <= LOAD_KEY;
                        busy <= '1';
                    end if;

                when LOAD_KEY =>
                    w(0) <= anahtar_giris(255 downto 224);
                    w(1) <= anahtar_giris(223 downto 192);
                    w(2) <= anahtar_giris(191 downto 160);
                    w(3) <= anahtar_giris(159 downto 128);
                    w(4) <= anahtar_giris(127 downto 96);
                    w(5) <= anahtar_giris(95 downto 64);
                    w(6) <= anahtar_giris(63 downto 32);
                    w(7) <= anahtar_giris(31 downto 0);
                    tur_indeksi <= to_unsigned(8, 6);
                    state <= EXPAND;

                when EXPAND =>
                    idx := to_integer(tur_indeksi);

                    if idx <= 59 then
                        gecici_kelime := w(idx - 1);

                        if (idx mod 8) = 0 then
                            gecici_kelime := kelime_dondur(gecici_kelime);
                            gecici_kelime := kelime_degistir(gecici_kelime);
                            rcon_val := RCON(idx / 8) & x"000000";
                            gecici_kelime := gecici_kelime xor rcon_val;
                        elsif (idx mod 8) = 4 then
                            gecici_kelime := kelime_degistir(gecici_kelime);
                        end if;

                        w(idx) <= w(idx - 8) xor gecici_kelime;
                        tur_indeksi <= tur_indeksi + 1;
                    else
                        state <= FINISHED;
                    end if;

                when FINISHED =>
                    for rk in 0 to 14 loop
                        tur_anahtarlari(rk) <= w(rk * 4) & w(rk * 4 + 1) & w(rk * 4 + 2) & w(rk * 4 + 3);
                    end loop;
                    state <= DONE_PULSE;

                when DONE_PULSE =>
                    done <= '1';
                    busy <= '0';
                    state <= IDLE;

                when others =>
                    state <= IDLE;
            end case;
        end if;
    end process;

end architecture rtl;
