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

        $assocBoardId = DB::table('boards')->insertGetId([
            'name' => 'bath-wells',
            'readable_name' => 'Bath & Wells',
            'created_by' => $user->id,
            'type' => BoardType::GUILD,
        ]);

        $branchBoardId = DB::table('boards')->insertGetId([
            'name' => 'bath-branch',
            'readable_name' => 'Bath Branch',
            'created_by' => $user->id,
            'type' => BoardType::BRANCH,
        ]);

        DB::table('board_affiliates')->insert([
            'board_id' => $branchBoardId,
            'affiliate_id' => $assocBoardId
        ]);

        DB::table('boards')->insert([
            'name' => 'toms-quarter-pealers',
            'readable_name' => 'Tom\'s Quarter Pealers',
            'created_by' => $user->id,
        ]);

        $tower = Tower::where('area', '=', 'Bathwick')->first();
        $boardId = DB::table('boards')->insertGetId([
            'name' => 'bathwick',
            'readable_name' => 'Bathwick',
            'website_url' => 'http://bathwick.brinkster.net',
            'address' => 'Darlington St, Bath',
            'postcode' => 'BA2 4EB',
            'twitter_handle' => 'tomlongridge',
            'facebook_url' => 'groups/bathwick.ringers',
            'info_parking' => 'Parking is available in the car park outside on practice evenings. ' .
                              'Otherwise you\'ll need to use on street parking.',
            'info_toilets' => 'Not usually accessible',
            'info_practices' => 'Wednesday, 7:30pm',
            'info_services' => 'Sunday, 9:15am, by arrangement',
            'latitude' => -2.351199,
            'longitude' => 51.384340,
            'created_by' => $user->id,
            'tower_id' => $tower->id,
            'type' => BoardType::TOWER,
        ]);

        DB::table('board_affiliates')->insert([
            'board_id' => $boardId,
            'affiliate_id' => $branchBoardId
        ]);

    }

}
