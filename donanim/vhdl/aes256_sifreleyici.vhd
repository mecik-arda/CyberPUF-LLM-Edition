library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity aes256_sifreleyici is
    port (
        clk             : in  std_logic;
        rst             : in  std_logic;
        duz_metin       : in  std_logic_vector(127 downto 0);
        tur_anahtarlari      : in  tur_anahtar_dizisi_t;
        start           : in  std_logic;
        sifreli_metin      : out std_logic_vector(127 downto 0);
        done            : out std_logic;
        busy            : out std_logic
    );
end entity aes256_sifreleyici;

architecture rtl of aes256_sifreleyici is

    type state_t is (IDLE, INIT_ADD_KEY, STALL_STATE, ROUND_SUB_BYTES, ROUND_MIX_COLUMNS, ROUND_ADD_KEY, FINAL_ADD_KEY, FINISHED);
    signal fsm_state : state_t;

    signal aes_state : durum_dizisi_t;
    signal round_num : unsigned(3 downto 0);

    -- SCA Countermeasures (Side-Channel Attack)
    signal lfsr_reg : std_logic_vector(31 downto 0) := x"ACE10001";
    signal noise_reg : std_logic_vector(31 downto 0) := (others => '0');
    attribute keep : string;
    attribute keep of noise_reg : signal is "true";
    signal stall_count : unsigned(1 downto 0) := "00";
    signal free_running_counter : unsigned(31 downto 0) := x"1337BEEF";

begin

    process(clk, rst)
        variable temp_state : durum_dizisi_t;
        variable t0, t1, t2, t3 : std_logic_vector(7 downto 0);
        variable rk_vec : std_logic_vector(127 downto 0);
        variable rk_state : durum_dizisi_t;
    begin
        if rst = '1' then
            fsm_state <= IDLE;
            done <= '0';
            busy <= '0';
            round_num <= (others => '0');
            sifreli_metin <= (others => '0');
            for r in 0 to 3 loop
                for c in 0 to 3 loop
                    aes_state(r, c) <= (others => '0');
                end loop;
            end loop;
            lfsr_reg <= x"ACE10001";
            noise_reg <= (others => '0');
            stall_count <= "00";
            free_running_counter <= x"1337BEEF";
        elsif rising_edge(clk) then
            free_running_counter <= free_running_counter + 1;
            lfsr_reg <= lfsr_reg(30 downto 0) & (lfsr_reg(31) xor lfsr_reg(21) xor lfsr_reg(1) xor lfsr_reg(0));
            noise_reg <= noise_reg(30 downto 0) & lfsr_reg(31);

            done <= '0';

            case fsm_state is
                when IDLE =>
                    busy <= '0';
                    if start = '1' then
                        aes_state <= vektorden_duruma(duz_metin);
                        round_num <= (others => '0');
                        busy <= '1';
                        
                        if free_running_counter = x"00000000" then
                            lfsr_reg <= x"ACE10001";
                        else
                            lfsr_reg <= std_logic_vector(free_running_counter);
                        end if;
                        
                        fsm_state <= INIT_ADD_KEY;
                    end if;

                when INIT_ADD_KEY =>
                    rk_vec := tur_anahtarlari(0);
                    rk_state := vektorden_duruma(rk_vec);
                    for r in 0 to 3 loop
                        for c in 0 to 3 loop
                            aes_state(r, c) <= aes_state(r, c) xor rk_state(r, c);
                        end loop;
                    end loop;
                    round_num <= to_unsigned(1, 4);
                    stall_count <= unsigned(lfsr_reg(1 downto 0));
                    fsm_state <= STALL_STATE;

                when STALL_STATE =>
                    if stall_count = "00" then
                        fsm_state <= ROUND_SUB_BYTES;
                    else
                        stall_count <= stall_count - 1;
                    end if;

                when ROUND_SUB_BYTES =>
                    -- Row 0: no shift
                    aes_state(0, 0) <= bayt_degistir(aes_state(0, 0));
                    aes_state(0, 1) <= bayt_degistir(aes_state(0, 1));
                    aes_state(0, 2) <= bayt_degistir(aes_state(0, 2));
                    aes_state(0, 3) <= bayt_degistir(aes_state(0, 3));

                    -- Row 1: shift 1 left
                    aes_state(1, 0) <= bayt_degistir(aes_state(1, 1));
                    aes_state(1, 1) <= bayt_degistir(aes_state(1, 2));
                    aes_state(1, 2) <= bayt_degistir(aes_state(1, 3));
                    aes_state(1, 3) <= bayt_degistir(aes_state(1, 0));

                    -- Row 2: shift 2 left
                    aes_state(2, 0) <= bayt_degistir(aes_state(2, 2));
                    aes_state(2, 1) <= bayt_degistir(aes_state(2, 3));
                    aes_state(2, 2) <= bayt_degistir(aes_state(2, 0));
                    aes_state(2, 3) <= bayt_degistir(aes_state(2, 1));

                    -- Row 3: shift 3 left
                    aes_state(3, 0) <= bayt_degistir(aes_state(3, 3));
                    aes_state(3, 1) <= bayt_degistir(aes_state(3, 0));
                    aes_state(3, 2) <= bayt_degistir(aes_state(3, 1));
                    aes_state(3, 3) <= bayt_degistir(aes_state(3, 2));

                    if round_num = to_unsigned(14, 4) then
                        fsm_state <= FINAL_ADD_KEY;
                    else
                        fsm_state <= ROUND_MIX_COLUMNS;
                    end if;

                when ROUND_MIX_COLUMNS =>
                    for c in 0 to 3 loop
                        t0 := aes_state(0, c);
                        t1 := aes_state(1, c);
                        t2 := aes_state(2, c);
                        t3 := aes_state(3, c);

                        aes_state(0, c) <= xtime(t0) xor (xtime(t1) xor t1) xor t2 xor t3;
                        aes_state(1, c) <= t0 xor xtime(t1) xor (xtime(t2) xor t2) xor t3;
                        aes_state(2, c) <= t0 xor t1 xor xtime(t2) xor (xtime(t3) xor t3);
                        aes_state(3, c) <= (xtime(t0) xor t0) xor t1 xor t2 xor xtime(t3);
                    end loop;
                    fsm_state <= ROUND_ADD_KEY;

                when ROUND_ADD_KEY =>
                    rk_vec := tur_anahtarlari(to_integer(round_num));
                    rk_state := vektorden_duruma(rk_vec);
                    for r in 0 to 3 loop
                        for c in 0 to 3 loop
                            aes_state(r, c) <= aes_state(r, c) xor rk_state(r, c);
                        end loop;
                    end loop;
                    round_num <= round_num + 1;
                    stall_count <= unsigned(lfsr_reg(1 downto 0));
                    fsm_state <= STALL_STATE;

                when FINAL_ADD_KEY =>
                    rk_vec := tur_anahtarlari(14);
                    rk_state := vektorden_duruma(rk_vec);
                    for r in 0 to 3 loop
                        for c in 0 to 3 loop
                            aes_state(r, c) <= aes_state(r, c) xor rk_state(r, c);
                        end loop;
                    end loop;
                    fsm_state <= FINISHED;


                when FINISHED =>
                    sifreli_metin <= durumdan_vektore(aes_state);
                    done <= '1';
                    busy <= '0';
                    fsm_state <= IDLE;

                when others =>
                    fsm_state <= IDLE;
            end case;
        end if;
    end process;

end architecture rtl;
