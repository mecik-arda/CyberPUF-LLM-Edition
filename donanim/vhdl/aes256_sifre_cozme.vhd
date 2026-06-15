library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity aes256_sifre_cozme is
    port (
        clk             : in  std_logic;
        rst             : in  std_logic;
        sifreli_metin      : in  std_logic_vector(127 downto 0);
        tur_anahtarlari      : in  tur_anahtar_dizisi_t;
        start           : in  std_logic;
        duz_metin       : out std_logic_vector(127 downto 0);
        done            : out std_logic;
        busy            : out std_logic
    );
end entity aes256_sifre_cozme;

architecture rtl of aes256_sifre_cozme is

    type state_t is (
        IDLE,
        INIT_ADD_KEY,
        INV_SHIFT_SUB_ADD,
        STALL_STATE,
        INV_MIX_COLUMNS,
        FINISHED
    );
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
            duz_metin <= (others => '0');
            lfsr_reg <= x"ACE10001";
            noise_reg <= (others => '0');
            stall_count <= "00";
            free_running_counter <= x"1337BEEF";
            for r in 0 to 3 loop
                for c in 0 to 3 loop
                    aes_state(r, c) <= (others => '0');
                end loop;
            end loop;
        elsif rising_edge(clk) then
            free_running_counter <= free_running_counter + 1;

            -- LFSR (32-bit Galois, taps: 32, 22, 2, 1) -> Indices 31, 21, 1, 0
            lfsr_reg <= lfsr_reg(30 downto 0) & (lfsr_reg(31) xor lfsr_reg(21) xor lfsr_reg(1) xor lfsr_reg(0));

            -- Dummy Power Noise (tek atama ile birlestirildi)
            noise_reg <= noise_reg(30 downto 0) & lfsr_reg(31);

            done <= '0';

            case fsm_state is
                when IDLE =>
                    busy <= '0';
                    if start = '1' then
                        aes_state <= vektorden_duruma(sifreli_metin);
                        round_num <= to_unsigned(14, 4);
                        busy <= '1';
                        
                        -- LFSR seed'ini dinamik serbest sayacla baslat
                        if free_running_counter = x"00000000" then
                            lfsr_reg <= x"ACE10001";
                        else
                            lfsr_reg <= std_logic_vector(free_running_counter);
                        end if;
                        
                        fsm_state <= INIT_ADD_KEY;
                    end if;

                when INIT_ADD_KEY =>
                    rk_vec := tur_anahtarlari(14);
                    rk_state := vektorden_duruma(rk_vec);
                    for r in 0 to 3 loop
                        for c in 0 to 3 loop
                            aes_state(r, c) <= aes_state(r, c) xor rk_state(r, c);
                        end loop;
                    end loop;
                    round_num <= to_unsigned(13, 4);
                    
                    stall_count <= unsigned(lfsr_reg(1 downto 0)); -- TODO: Needs better TRNG for wider stall_count
                    fsm_state <= STALL_STATE;

                when INV_SHIFT_SUB_ADD =>
                    rk_vec := tur_anahtarlari(to_integer(round_num));
                    rk_state := vektorden_duruma(rk_vec);

                    -- Row 0
                    aes_state(0, 0) <= ters_bayt_degistir(aes_state(0, 0)) xor rk_state(0, 0);
                    aes_state(0, 1) <= ters_bayt_degistir(aes_state(0, 1)) xor rk_state(0, 1);
                    aes_state(0, 2) <= ters_bayt_degistir(aes_state(0, 2)) xor rk_state(0, 2);
                    aes_state(0, 3) <= ters_bayt_degistir(aes_state(0, 3)) xor rk_state(0, 3);

                    -- Row 1: shift 1 right
                    aes_state(1, 0) <= ters_bayt_degistir(aes_state(1, 3)) xor rk_state(1, 0);
                    aes_state(1, 1) <= ters_bayt_degistir(aes_state(1, 0)) xor rk_state(1, 1);
                    aes_state(1, 2) <= ters_bayt_degistir(aes_state(1, 1)) xor rk_state(1, 2);
                    aes_state(1, 3) <= ters_bayt_degistir(aes_state(1, 2)) xor rk_state(1, 3);

                    -- Row 2: shift 2 right
                    aes_state(2, 0) <= ters_bayt_degistir(aes_state(2, 2)) xor rk_state(2, 0);
                    aes_state(2, 1) <= ters_bayt_degistir(aes_state(2, 3)) xor rk_state(2, 1);
                    aes_state(2, 2) <= ters_bayt_degistir(aes_state(2, 0)) xor rk_state(2, 2);
                    aes_state(2, 3) <= ters_bayt_degistir(aes_state(2, 1)) xor rk_state(2, 3);

                    -- Row 3: shift 3 right
                    aes_state(3, 0) <= ters_bayt_degistir(aes_state(3, 1)) xor rk_state(3, 0);
                    aes_state(3, 1) <= ters_bayt_degistir(aes_state(3, 2)) xor rk_state(3, 1);
                    aes_state(3, 2) <= ters_bayt_degistir(aes_state(3, 3)) xor rk_state(3, 2);
                    aes_state(3, 3) <= ters_bayt_degistir(aes_state(3, 0)) xor rk_state(3, 3);

                    if round_num = to_unsigned(0, 4) then
                        fsm_state <= FINISHED;
                    else
                        fsm_state <= INV_MIX_COLUMNS;
                    end if;

                when STALL_STATE =>
                    if stall_count = "00" then
                        fsm_state <= INV_SHIFT_SUB_ADD;
                    else
                        stall_count <= stall_count - 1;
                    end if;

                when INV_MIX_COLUMNS =>
                    for c in 0 to 3 loop
                        t0 := aes_state(0, c);
                        t1 := aes_state(1, c);
                        t2 := aes_state(2, c);
                        t3 := aes_state(3, c);

                        aes_state(0, c) <= gf_carpim(t0, 14) xor gf_carpim(t1, 11) xor gf_carpim(t2, 13) xor gf_carpim(t3, 9);
                        aes_state(1, c) <= gf_carpim(t0, 9)  xor gf_carpim(t1, 14) xor gf_carpim(t2, 11) xor gf_carpim(t3, 13);
                        aes_state(2, c) <= gf_carpim(t0, 13) xor gf_carpim(t1, 9)  xor gf_carpim(t2, 14) xor gf_carpim(t3, 11);
                        aes_state(3, c) <= gf_carpim(t0, 11) xor gf_carpim(t1, 13) xor gf_carpim(t2, 9)  xor gf_carpim(t3, 14);
                    end loop;

                    round_num <= round_num - 1;
                    stall_count <= unsigned(lfsr_reg(1 downto 0)); -- TODO: Needs better TRNG for wider stall_count
                    fsm_state <= STALL_STATE;
                when FINISHED =>
                    duz_metin <= durumdan_vektore(aes_state);
                    done <= '1';
                    busy <= '0';
                    fsm_state <= IDLE;

                when others =>
                    fsm_state <= IDLE;
            end case;
        end if;
    end process;

end architecture rtl;
