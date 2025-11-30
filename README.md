## How to build and run 

The build is a simple standard build using: 
```
cd PIRTemplate/ && idf.py flash
```

**Special note**

My air sensor is a SCD40 that I have laying around that measures CO2 level as well. The datasheet can be found here: 
https://sensirion.com/media/documents/E0F04247/631EF271/CD_DS_SCD40_SCD41_Datasheet_D1.pdf

I wrote some bare metal commands for it in the file `co2.c`. If you need hardware to test, I have two more for spare.

The code is available on https://github.com/chedinhtrung/iot_lab if I make any further changes.