<?php

use Illuminate\Database\Seeder;
use App\User;
use App\Board;
use App\Enums\SubscriptionType;
use Carbon\Carbon;

class SubscriptionTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        User::all()->each(function($user) {
            Board::all()->each(function($board) use ($user) {
                if (Str::contains($user->email, "tomlongridge")) {
                    $subscribe = 1;
                    $subType = SubscriptionType::ADMIN;
                } else {
                    $subscribe = rand(0, 1);
                    $subType = Arr::random(SubscriptionType::getInstances())->value;
                }
                if ($subscribe) {
                    DB::table('board_subscriptions')->insert([
                      'board_id' => $board->id,
                      'user_id' => $user->id,
                      'type' => $subType,
                      'created_at' => Carbon::now()->subtract(rand(0, 365), 'day')
                    ]);
                }
            });
        });
    }
}
