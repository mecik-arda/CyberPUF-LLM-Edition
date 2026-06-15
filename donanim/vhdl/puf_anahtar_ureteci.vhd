library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity puf_anahtar_ureteci is
    generic (
        KEY_WIDTH        : integer := 256;
        RO_CIFT_SAYISI     : integer := 256;
        INVERTER_SAYISI    : integer := 3;
        SAYICI_GENISLIGI    : integer := 20;
        SAYMA_DONGULERI     : integer := 1000;
        REPETITIONS      : integer := 15
    );
    port (
        clk             : in  std_logic;
        rst             : in  std_logic;
        anahtar_uret    : in  std_logic;
        puf_anahtar         : out std_logic_vector(KEY_WIDTH - 1 downto 0);
        anahtar_gecerli       : out std_logic;
        busy            : out std_logic;
        bit_indeks_cikis   : out std_logic_vector(8 downto 0);
        hata_ayiklama_sayac_a   : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
        hata_ayiklama_sayac_b   : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0)
    );
end entity puf_anahtar_ureteci;

architecture rtl of puf_anahtar_ureteci is

    type state_t is (
        IDLE,
        START_PUF,
        WAIT_PUF,
        STORE_BIT,
        NEXT_BIT,
        KEY_READY
    );
    signal state : state_t;

    signal puf_start       : std_logic;
    signal puf_challenge   : std_logic_vector(7 downto 0);
    signal puf_response    : std_logic;
    signal puf_valid       : std_logic;
    signal puf_mesgul        : std_logic;
    signal puf_count_a     : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
    signal puf_count_b     : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);

    signal key_reg         : std_logic_vector(KEY_WIDTH - 1 downto 0);
    signal bit_counter     : unsigned(8 downto 0);
    signal challenge_idx   : unsigned(7 downto 0);
    signal rep_counter     : unsigned(4 downto 0);

    signal accumulated_bit : unsigned(4 downto 0);

    type helper_data_array is array(0 to KEY_WIDTH - 1) of std_logic;
    -- Ornek Helper Data ROM (Pratikte enrollment sirasinda belirlenir)
    constant HELPER_DATA_ROM : helper_data_array := (
        others => '0' 
    );

    component ro_puf_cekirdek is
        generic (
            RO_CIFT_SAYISI     : integer := 256;
            INVERTER_SAYISI    : integer := 3;
            SAYICI_GENISLIGI    : integer := 20;
            SAYMA_DONGULERI     : integer := 1000
        );
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            start           : in  std_logic;
            challenge       : in  std_logic_vector(7 downto 0);
            response_bit    : out std_logic;
            response_valid  : out std_logic;
            busy            : out std_logic;
            ro_count_a      : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
            ro_count_b      : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0)
        );
    end component;

begin

    assert REPETITIONS <= 32 report "REPETITIONS 32'den buyuk olamaz!" severity failure;

    puf_inst: ro_puf_cekirdek
        generic map (
            RO_CIFT_SAYISI  => RO_CIFT_SAYISI,
            INVERTER_SAYISI => INVERTER_SAYISI,
            SAYICI_GENISLIGI => SAYICI_GENISLIGI,
            SAYMA_DONGULERI  => SAYMA_DONGULERI
        )
        port map (
            clk           => clk,
            rst           => rst,
            start         => puf_start,
            challenge     => puf_challenge,
            response_bit  => puf_response,
            response_valid => puf_valid,
            busy          => puf_mesgul,
            ro_count_a    => puf_count_a,
            ro_count_b    => puf_count_b
        );

    hata_ayiklama_sayac_a <= puf_count_a;
    hata_ayiklama_sayac_b <= puf_count_b;
    bit_indeks_cikis <= std_logic_vector(bit_counter);

    process(clk, rst)
        variable majority_result : std_logic;
    begin
        if rst = '1' then
            state <= IDLE;
            key_reg <= (others => '0');
            puf_anahtar <= (others => '0');
            anahtar_gecerli <= '0';
            busy <= '0';
            puf_start <= '0';
            puf_challenge <= (others => '0');
            bit_counter <= (others => '0');
            challenge_idx <= (others => '0');
            rep_counter <= (others => '0');
            accumulated_bit <= (others => '0');
        elsif rising_edge(clk) then
            puf_start <= '0';
            anahtar_gecerli <= '0';

            case state is
                when IDLE =>
                    busy <= '0';
                    if anahtar_uret = '1' then
                        key_reg <= (others => '0');
                        bit_counter <= (others => '0');
                        challenge_idx <= (others => '0');
                        accumulated_bit <= (others => '0');
                        rep_counter <= (others => '0');
                        busy <= '1';
                        state <= START_PUF;
                    end if;

                when START_PUF =>
                    puf_challenge <= std_logic_vector(challenge_idx);
                    puf_start <= '1';
                    state <= WAIT_PUF;

                when WAIT_PUF =>
                    if puf_valid = '1' then
                        if puf_response = '1' then
                            accumulated_bit <= accumulated_bit + 1;
                        end if;
                        rep_counter <= rep_counter + 1;

                        if rep_counter = to_unsigned(REPETITIONS - 1, 5) then
                            state <= STORE_BIT;
                        else
                            state <= START_PUF;
                        end if;
                    end if;

                when STORE_BIT =>
                    if accumulated_bit > to_unsigned(REPETITIONS / 2, 5) then
                        majority_result := '1';
                    else
                        majority_result := '0';
                    end if;

                    -- Fuzzy Extractor: Repetition Code Decode + Helper Data XOR
                    key_reg(KEY_WIDTH - 1 - to_integer(bit_counter)) <= majority_result xor HELPER_DATA_ROM(to_integer(bit_counter));

                    accumulated_bit <= (others => '0');
                    rep_counter <= (others => '0');

                    state <= NEXT_BIT;

                when NEXT_BIT =>
                    if bit_counter = to_unsigned(KEY_WIDTH - 1, 9) then
                        state <= KEY_READY;
                    else
                        bit_counter <= bit_counter + 1;

                        if challenge_idx = to_unsigned(RO_CIFT_SAYISI - 1, 8) then
                            challenge_idx <= (others => '0');
                        else
                            challenge_idx <= challenge_idx + 1;
                        end if;

                        state <= START_PUF;
                    end if;

                when KEY_READY =>
                    puf_anahtar <= key_reg;
                    anahtar_gecerli <= '1';
                    busy <= '0';
                    state <= IDLE;

                when others =>
                    state <= IDLE;
            end case;
        end if;
    end process;

end architecture rtl;
