<?php

use Illuminate\Database\Seeder;
use App\Tower;
use App\User;
use App\Enums\BoardType;

use Carbon\Carbon;
use App\Enums\SubscriptionType;

class BoardsTableSeeder extends Seeder{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $user = User::where('email', '=', 'tomlongridge@gmail.com')->first();
        $user_mem = User::where('email', '=', 'tomlongridge+ann@gmail.com')->first();
        $user_sub = User::where('email', '=', 'tomlongridge+sue@gmail.com')->first();

        $assocBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bath & Wells',
            'created_by' => $user->id,
            'type' => BoardType::GUILD,
        ]);

        $branchBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bath Branch',
            'created_by' => $user->id,
            'type' => BoardType::BRANCH,
        ]);

        DB::table('board_affiliates')->insert([
            'board_id' => $branchBoardId,
            'affiliate_id' => $assocBoardId
        ]);

        DB::table('boards')->insert([
            'name' => 'Tom\' Quarter Pealers',
            'created_by' => $user->id,
        ]);

        $tower = Tower::where('area', '=', 'Bathwick')->first();
        $towerBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bathwick',
            'website_url' => 'http://bathwick.brinkster.net',
            'created_by' => $user->id,
            'tower_id' => $tower->id,
            'type' => BoardType::TOWER,
        ]);

        DB::table('board_affiliates')->insert([
            'board_id' => $towerBoardId,
            'affiliate_id' => $branchBoardId
        ]);

        DB::table('notices')->insert([
            'board_id' => $towerBoardId,
            'title' => 'Practice Cancelled on Thursday 3rd May',
            'body' => 'There will be no practice on the 3rd May due to a choir practice',
            'created_at' => Carbon::now()->subtract(7, 'day'),
            'created_by' => $user->id,
        ]);

        DB::table('notices')->insert([
            'board_id' => $towerBoardId,
            'title' => 'Tower Outing',
            'body' => 'We\`re going on an outing on the 7th September. Let me know if you want to come!',
            'created_at' => Carbon::now()->subtract(3, 'day'),
            'created_by' => $user->id,
        ]);

        DB::table('board_subscriptions')->insert([
            [
                'board_id' => $towerBoardId,
                'user_id' => $user_sub->id,
                'type' => SubscriptionType::BASIC,
                'created_at' => Carbon::now()->subtract(3, 'day')
            ],
            [
                'board_id' => $towerBoardId,
                'user_id' => $user_mem->id,
                'type' => SubscriptionType::MEMBER,
                'created_at' => Carbon::now()->subtract(3, 'day')
            ],
            [
                'board_id' => $towerBoardId,
                'user_id' => $user->id,
                'type' => SubscriptionType::ADMIN,
                'created_at' => Carbon::now()->subtract(3, 'day')
            ]
        ]);

    }

}
