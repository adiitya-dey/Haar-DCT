# add --individual for DLinear-I
if [ ! -d "./logs" ]; then
    mkdir ./logs
fi

if [ ! -d "./logs/LongForecasting" ]; then
    mkdir ./logs/LongForecasting
fi
seq_len=104
model_name=ESN
root_path_name=./dataset/
data_path=national_illness.csv
model_id_name=national_illness
data=custom
window_len=4 
reservoir_size=25
washout=4
model_id='ILI_'$seq_len'_'$pred_len



random_seed=2021
for pred_len in 24 36 48 60
do
    model_id=$data'_'$seq_len'_'$pred_len
    python -u run_longExp.py \
      --random_seed $random_seed \
      --is_training 1 \
      --root_path ./dataset/ \
      --data_path $data_path \
      --model_id $model_id \
      --model $model_name \
      --data $data \
      --features M \
      --seq_len $seq_len \
      --pred_len $pred_len \
      --window_len $window_len \
      --reservoir_size $reservoir_size \
      --washout $washout \
      --enc_in 7 \
      --individual 1 \
      --des 'Exp' \
      --train_epochs 30\
      --loss 'mse' \
      --itr 1 --batch_size 16 --learning_rate 0.01 >logs/LongForecasting/$model_name'_'$model_id_name'_'$seq_len'_'$pred_len.log 
done