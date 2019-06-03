<?php

use Illuminate\Database\Seeder;
use App\Tower;
use App\User;
use App\Enums\BoardType;

class BoardsTableSeeder extends Seeder{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $user = User::where('email', '=', 'tomlongridge@gmail.com')->first();

        $assocBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bath & Wells',
            'owner_id' => $user->id,
            'type' => BoardType::GUILD,
        ]);

        $branchBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bath Branch',
            'owner_id' => $user->id,
            'type' => BoardType::BRANCH,
        ]);

        DB::table('board_affiliates')->insert([
            'board_id' => $branchBoardId,
            'affiliate_id' => $assocBoardId
        ]);

        DB::table('boards')->insert([
            'name' => 'Tom\' Quarter Pealers',
            'owner_id' => $user->id,
        ]);

        $tower = Tower::where('area', '=', 'Bathwick')->first();
        $towerBoardId = DB::table('boards')->insertGetId([
            'name' => 'Bathwick',
            'website_url' => 'http://bathwick.brinkster.net',
            'owner_id' => $user->id,
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
            'body' => 'There will be no practice on the 3rd May due to a choir practice'
        ]);

        DB::table('notices')->insert([
            'board_id' => $towerBoardId,
            'title' => 'Tower Outing',
            'body' => 'Wequot;re going on an outing on the 7th September. Let me know if you want to come!'
        ]);

    }

}