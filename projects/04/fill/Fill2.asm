/* Initialize row, col to 0
 * Set pixPtr to SCREEN address 
 * For each col from 0 to 512/16=32-1 (0..31):
 *   For each row from 0 to 256       
 *   If KBD DATA is not 0: set RAM[SCREEN+row*32+col/16] to -1 (all 1s)
*   Else: set RAM[SCREEN+row*32+col/16] to 0 
*   Increment col
