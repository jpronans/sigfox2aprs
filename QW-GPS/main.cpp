include "mbed.h"

DigitalOut LED_0 (PB_6);
DigitalOut LED_1 (PA_7);
DigitalOut LED_2 (PA_6);
DigitalOut LED_3 (PA_5);
InterruptIn SW1(PB_10);
InterruptIn SW2(PA_8);

Ticker hartbeat;
Ticker position_update;

//Virtual serial port over USB
Serial pc(USBTX, USBRX);
Serial modem(PA_9, PA_10);

char * response = "OK";
char * responsePtr;
bool commandogiven = false;
bool commandofailed = true;
int updateinterval_s = 600;

// Send command and check if ok
void command(char * commando)
{
    LED_1=0;
    modem.printf(commando);
    commandogiven = true;
    commandofailed = true;
}

// Blinking LED Ticker
void beat()
{
    LED_0 = !LED_0;
}

// Position transmission ticker
void txpos()
{
    command("AT$GSND\n");
}

void sw1interrupt()
{
    //command("AT$GPS=1,16,0,65535,1,1\n");
    if(updateinterval_s == 1800)
    {   
        position_update.detach();
        updateinterval_s = 600; // Updateinterval = 10 minutes
        LED_3 = 1;
        LED_2 = 0;
        position_update.attach(&txpos, updateinterval_s);
    }
    else
    {   
        position_update.detach();
        updateinterval_s = 1800; // Updateinterval = 30 minutes
        LED_3 = 0;
        LED_2 = 1;
        position_update.attach(&txpos, updateinterval_s);
    }
}

void sw2interrupt()
{
    command("AT$GSND\n");
}

int main()
{
    wait(3);
    LED_0 = 1;
    LED_1 = 1;
    LED_2 = 1;
    LED_3 = 0;
    hartbeat.attach(&beat, 0.5);
    position_update.attach(&txpos, updateinterval_s);
    SW2.fall(&sw1interrupt);
    SW1.fall(&sw2interrupt);
    command("AT$GPS=1,16,0,65535,1,1\n");
    while(1) {
        if(!commandogiven) {
            if(pc.readable()) {
                modem.putc(pc.getc());
            }

            if(modem.readable()) {
                pc.putc(modem.getc());
            }
        } else {
            int c, i;
            while ((c = modem.getc()) >= 0 && commandogiven && i < 10000) {
                if ((char) c == *responsePtr)
                    responsePtr++;
                else
                    responsePtr = response;
                if (*responsePtr == 0) {
                    LED_1=1;
                    commandogiven = false;
                }
                i++;
            }
            if(commandogiven == true) {
                commandogiven = false;
                commandofailed = true;
                LED_1=1;
            } else {
                commandofailed = false;
            }

        }
    }
}
